import importlib.util, json, sys, unittest
from pathlib import Path

SCRIPT=Path(__file__).parents[1]/"scripts"/"upstream_watch.py"
spec=importlib.util.spec_from_file_location("watch",SCRIPT); watch=importlib.util.module_from_spec(spec); sys.modules[spec.name]=watch; spec.loader.exec_module(watch)

class WatchTests(unittest.TestCase):
    def test_relevant_commit_filter_excludes_noise_and_keeps_p2pdma(self):
        source={"id":"linux-mainline-p2pdma","kind":"github_commit","category":"linux-p2pdma"}
        raw=json.dumps([
          {"sha":"a"*40,"html_url":"https://github.com/a","commit":{"message":"PCI/P2PDMA: support Intel Xeon"}},
          {"sha":"b"*40,"html_url":"https://github.com/b","commit":{"message":"docs: fix typo"}}
        ]).encode()
        found=[x for x in watch.normalize(source,raw) if watch.relevant(x,source)]
        self.assertEqual([x["id"] for x in found],["a"*40])

    def test_stable_tree_commits_are_not_labeled_mainline(self):
        source={"id":"linux-stable-p2pdma","kind":"github_commit","category":"linux-stable-p2pdma"}
        raw=json.dumps([{"sha":"a"*40,"html_url":"https://github.com/a","commit":{"message":"PCI/P2PDMA: fix peer transfer"}}]).encode()
        self.assertIn("stable-tree commit",watch.normalize(source,raw)[0]["status"])

    def test_nvidia_release_baseline_filters_existing_releases(self):
        source={"id":"nvidia-open-modules","kind":"github_releases"}
        raw=json.dumps([
          {"tag_name":"580.196.07","name":"baseline","html_url":"https://github.com/nvidia/base","draft":False,"prerelease":False},
          {"tag_name":"580.196.06","name":"older","html_url":"https://github.com/nvidia/old","draft":False,"prerelease":False},
          {"tag_name":"580.196.11","name":"newer","html_url":"https://github.com/nvidia/new","draft":False,"prerelease":False},
          {"tag_name":"581.2.0-rc1","name":"beta","prerelease":True}
        ]).encode()
        self.assertEqual([x["id"] for x in watch.normalize(source,raw)],["580.196.11"])

    def test_digest_key_stays_stable_for_unchanged_item_set(self):
        items=[watch.item("source",i,i,"https://example.test") for i in ("a","b")]
        self.assertEqual(watch.digest(items)["key"],watch.digest(list(reversed(items)))["key"])
        self.assertEqual(watch.digest(items)["key"],watch.digest(items)["key"])

    def test_digest_contains_every_item(self):
        items=[watch.item("source",str(i),f"update {i}",f"https://example.test/{i}") for i in range(25)]
        report=watch.digest(items)
        self.assertEqual(report["item_count"],25)
        for x in items:
            self.assertIn(x["title"],report["summary"])

    def test_digest_rejects_untrusted_and_escapes_markdown_urls(self):
        self.assertIsNone(watch.safe_markdown_url("https://evil.example/path","nvidia-open-modules"))
        self.assertIsNone(watch.safe_markdown_url("https://github.com@evil.example/path","nvidia-open-modules"))
        self.assertIsNone(watch.safe_markdown_url("javascript:alert(1)","nvidia-open-modules"))
        x=watch.item("nvidia-open-modules","x","[evil](https://evil.example)","https://github.com/NVIDIA/open-gpu-kernel-modules/releases/tag/x%29](https://evil.example)")
        report=watch.digest([x])
        self.assertIn("https://github.com/NVIDIA/open-gpu-kernel-modules/releases/tag/x%29%5D%28https://evil.example%29",report["summary"])
        self.assertNotIn("](https://evil.example)",report["summary"])
        self.assertNotIn("[evil]",report["summary"])

    def test_changing_feed_only_alerts_new_items(self):
        a=watch.item("source","a","update a","https://example.test/a")
        b=watch.item("source","b","update b","https://example.test/b")
        c=watch.item("source","c","update c","https://example.test/c")
        prior=watch.digest([a,b])
        bodies=[f'<!-- upstream-watch:{prior["key"]} -->\n{prior["item_markers"]}\n{prior["summary"]}']
        self.assertEqual(watch.unseen_items([a,b,c],bodies),[c])
        new_digest=watch.digest(watch.unseen_items([a,b,c],bodies))
        bodies.append(f'<!-- upstream-watch:{new_digest["key"]} -->\n{new_digest["item_markers"]}\n{new_digest["summary"]}')
        self.assertEqual(watch.unseen_items([a,b,c],bodies),[])

    def test_item_markers_deduplicate_individual_alerts(self):
        a=watch.item("source","a","update a","https://example.test/a")
        b=watch.item("source","b","update b","https://example.test/b")
        prior=watch.digest([a])
        bodies=[f'<!-- upstream-watch:{prior["key"]} -->\n{prior["item_markers"]}']
        self.assertEqual(watch.unseen_items([a,b],bodies),[b])

    def test_unraid_stable_known_update_is_not_hidden_by_first_run_baseline(self):
        src={"id":"unraid-stable-notes","kind":"unraid_notes","baseline":"7.4.0","channel":"stable"}
        fixture='''<ul><li><a href="https://docs.unraid.net/unraid-os/release-notes/7.4.1/">7.4.1</a></li><li><a href="/unraid-os/release-notes/7.4.0/">7.4.0</a></li><li><a href="/unraid-os/release-notes/7.5.0-rc1/">7.5.0-rc1</a></li></ul>'''.encode()
        found=watch.normalize(src,fixture)
        self.assertEqual([(x["id"],x["status"]) for x in found],[("7.4.1","released")])
    def test_preview_is_separate_and_kernel_candidate_status_not_release(self):
        src={"id":"unraid-preview-notes","kind":"unraid_notes","baseline":"7.4.0","channel":"preview"}
        fixture=b'<a href="/unraid-os/release-notes/7.5.0-rc1/">7.5.0-rc1</a>'
        from unittest.mock import patch
        with patch.object(watch,"request",return_value=b"<p>no kernel version here</p>"):
            found=watch.normalize(src,fixture)
        self.assertEqual(found[0]["status"],"preview")
        self.assertEqual(found[0]["source"],"unraid-preview-notes")
    def test_kernel_versions_above_build_baseline_only(self):
        src={"id":"linux-kernel-releases","kind":"kernel_releases"}
        raw=json.dumps({"releases":[{"version":"6.18.60","moniker":"longterm"},{"version":"6.18.65","moniker":"longterm","tarball":"https://kernel.org/6.18.65"},{"version":"7.4-rc4","moniker":"mainline"}]}).encode()
        self.assertEqual([x["id"] for x in watch.normalize(src,raw)],["6.18.65"])

    def test_publishing_workflow_serializes_issue_writers(self):
        workflow=(SCRIPT.parents[1]/".github"/"workflows"/"upstream-watch.yml").read_text()
        publish=workflow.split("  publish:",1)[1]
        self.assertIn("concurrency:",publish)
        self.assertIn("group: upstream-alert-publisher-${{ github.repository }}",publish)
        self.assertIn("cancel-in-progress: false",publish)

if __name__=="__main__": unittest.main()
