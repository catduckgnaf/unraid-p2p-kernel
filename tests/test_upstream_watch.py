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

    def test_commit_feed_fetches_relevant_items_from_later_pages(self):
        from unittest.mock import patch
        source={"id":"linux-mainline-p2pdma","kind":"github_commit","category":"linux-p2pdma","url":"https://api.github.com/repos/torvalds/linux/commits?path=drivers/pci/p2pdma.c&per_page=30"}
        page_one=[{"sha":str(i),"html_url":"https://github.com/torvalds/linux/commit/"+str(i),"commit":{"message":"docs: unrelated update"}} for i in range(30)]
        page_two=[{"sha":"later","html_url":"https://github.com/torvalds/linux/commit/later","commit":{"message":"PCI/P2PDMA: improve peer transfer"}}]
        with patch.object(watch,"CONFIG",{"sources":[source]}), patch.object(watch,"request",side_effect=[json.dumps(page_one).encode(),json.dumps(page_two).encode()]) as fetch:
            rows,failures=watch.fetch_all()
        self.assertEqual(failures,[])
        self.assertEqual([x["id"] for x,_ in rows],["later"])
        self.assertEqual(fetch.call_count,2)
        self.assertIn("page=2",fetch.call_args_list[1].args[0])

    def test_amdgpu_commit_filter_keeps_drm_amd_subject_prefix(self):
        source={"id":"linux-drm-amdgpu","kind":"github_commit","category":"linux-drm-amdgpu"}
        raw=json.dumps([{"sha":"c"*40,"html_url":"https://github.com/a","commit":{"message":"drm/amd/display: fix connector hotplug handling"}}]).encode()
        found=[x for x in watch.normalize(source,raw) if watch.relevant(x,source)]
        self.assertEqual([x["id"] for x in found],["c"*40])

    def test_stable_tree_commits_are_not_labeled_mainline(self):
        source={"id":"linux-stable-p2pdma","kind":"github_commit","category":"linux-stable-p2pdma"}
        raw=json.dumps([{"sha":"a"*40,"html_url":"https://github.com/a","commit":{"message":"PCI/P2PDMA: fix peer transfer"}}]).encode()
        self.assertIn("stable-tree commit",watch.normalize(source,raw)[0]["status"])

    def test_intel_release_notes_emit_every_listed_version(self):
        source={"id":"intel-gpu-release-notes","kind":"html_page","url":"https://dgpu-docs.intel.com/releases/release-notes.html"}
        fixture=b'''<ul><li>Release 2025.01.01</li><li>Release 2025.02.01</li><li>Release 2025.03.01</li></ul>'''
        found=watch.normalize(source,fixture)
        self.assertEqual([x["id"] for x in found],["2025.02.01","2025.03.01"])

    def test_intel_release_cutoff_excludes_historical_versions_on_fresh_scan(self):
        source={"id":"intel-gpu-release-notes","kind":"html_page","url":"https://dgpu-docs.intel.com/releases/release-notes.html"}
        fixture=b'''<ul><li>Release 2024.12.01</li><li>Release 2025.01.01</li><li>Release 2025.02.01</li></ul>'''
        found=watch.normalize(source,fixture)
        self.assertEqual([x["id"] for x in found],["2025.02.01"])

    def test_multiple_unraid_detail_failures_count_as_one_failed_feed(self):
        from unittest.mock import patch
        src={"id":"unraid-preview-notes","kind":"unraid_notes","baseline":"7.4.0","channel":"preview","url":"https://docs.unraid.net/category/release-notes/"}
        fixture=b'''<a href="/unraid-os/release-notes/7.5.0-rc1/">7.5.0-rc1</a><a href="/unraid-os/release-notes/7.5.0-rc2/">7.5.0-rc2</a><a href="/unraid-os/release-notes/7.5.0-rc3/">7.5.0-rc3</a>'''
        failures=[]
        with patch.object(watch,"request",side_effect=OSError("detail unavailable")):
            found=watch.normalize(src,fixture,failures)
        self.assertEqual([x["id"] for x in found],["7.5.0-rc1","7.5.0-rc2","7.5.0-rc3"])
        self.assertEqual(len(failures),3)
        self.assertEqual(watch.successful_feed_count(failures),len(watch.CONFIG["sources"])-1)
        self.assertGreaterEqual(watch.successful_feed_count(failures),0)

    def test_unraid_detail_fetch_failure_is_reported_and_release_preserved(self):
        from unittest.mock import patch
        src={"id":"unraid-preview-notes","kind":"unraid_notes","baseline":"7.4.0","channel":"preview","url":"https://docs.unraid.net/category/release-notes/"}
        fixture=b'<a href="/unraid-os/release-notes/7.5.0-rc1/">7.5.0-rc1</a>'
        failures=[]
        with patch.object(watch,"request",side_effect=OSError("detail unavailable")):
            found=watch.normalize(src,fixture,failures)
        self.assertEqual([x["id"] for x in found],["7.5.0-rc1"])
        self.assertIn("shipped kernel version not found",found[0]["summary"])
        self.assertEqual(failures,[{"source":"unraid-preview-notes","item":"7.5.0-rc1","error":"detail fetch failed: detail unavailable"}])

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
        self.assertIsNone(watch.safe_markdown_url("https://github.com:bad/path","nvidia-open-modules"))
        self.assertIsNone(watch.safe_markdown_url("https://github.com:99999/path","nvidia-open-modules"))
        self.assertIsNone(watch.safe_markdown_url("https://[invalid/path","nvidia-open-modules"))
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

    def test_shared_feed_url_does_not_hide_new_intel_release(self):
        old=watch.item("intel-gpu-release-notes","2025.01.01","Intel release 2025.01.01","https://dgpu-docs.intel.com/releases/release-notes.html")
        new=watch.item("intel-gpu-release-notes","2025.02.01","Intel release 2025.02.01","https://dgpu-docs.intel.com/releases/release-notes.html")
        prior=watch.digest([old])
        bodies=[f'<!-- upstream-watch:{prior["key"]} -->\n{prior["item_markers"]}\n{prior["summary"]}']
        self.assertEqual(watch.unseen_items([new],bodies),[new])

    def test_item_markers_deduplicate_individual_alerts(self):
        a=watch.item("source","a","update a","https://example.test/a")
        b=watch.item("source","b","update b","https://example.test/b")
        prior=watch.digest([a])
        bodies=[f'<!-- upstream-watch:{prior["key"]} -->\n{prior["item_markers"]}']
        self.assertEqual(watch.unseen_items([a,b],bodies),[b])

    def test_unraid_stable_known_update_is_not_hidden_by_first_run_baseline(self):
        src={"id":"unraid-stable-notes","kind":"unraid_notes","baseline":"7.4.0","channel":"stable","url":"https://docs.unraid.net/category/release-notes/"}
        fixture='''<ul><li><a href="https://docs.unraid.net/unraid-os/release-notes/7.4.1/">7.4.1</a></li><li><a href="/unraid-os/release-notes/7.4.0/">7.4.0</a></li><li><a href="/unraid-os/release-notes/7.5.0-rc1/">7.5.0-rc1</a></li></ul>'''.encode()
        found=watch.normalize(src,fixture)
        self.assertEqual([(x["id"],x["status"]) for x in found],[("7.4.1","released")])
    def test_preview_is_separate_and_kernel_candidate_status_not_release(self):
        src={"id":"unraid-preview-notes","kind":"unraid_notes","baseline":"7.4.0","channel":"preview","url":"https://docs.unraid.net/category/release-notes/"}
        fixture=b'<a href="/unraid-os/release-notes/7.5.0-rc1/">7.5.0-rc1</a>'
        from unittest.mock import patch
        with patch.object(watch,"request",return_value=b"<p>no kernel version here</p>"):
            found=watch.normalize(src,fixture)
        self.assertEqual(found[0]["status"],"preview")
        self.assertEqual(found[0]["source"],"unraid-preview-notes")
    def test_unraid_detail_fetch_disables_redirects(self):
        from unittest.mock import patch, MagicMock, Mock
        opener=Mock()
        response=MagicMock()
        response.__enter__.return_value.read.return_value=b"<p>6.18.70-Unraid</p>"
        opener.open.return_value=response
        with patch.object(watch.urllib.request,"build_opener",return_value=opener) as build:
            self.assertEqual(watch.request("https://docs.unraid.net/release-notes/7.5.2/",allow_redirects=False),b"<p>6.18.70-Unraid</p>")
        handler=build.call_args.args[0]
        self.assertIs(handler,watch._RejectRedirects)
        self.assertIsNone(handler().redirect_request(None,None,302,"Found",{},"https://127.0.0.1/"))
        opener.open.assert_called_once()

    def test_all_upstream_requests_reject_redirects_by_default(self):
        from unittest.mock import patch, MagicMock, Mock
        opener=Mock()
        response=MagicMock()
        response.__enter__.return_value.read.return_value=b"[]"
        opener.open.return_value=response
        with patch.object(watch.urllib.request,"build_opener",return_value=opener) as build:
            self.assertEqual(watch.request("https://api.github.com/repos/example/project/releases"),b"[]")
        handler=build.call_args.args[0]
        self.assertIs(handler,watch._RejectRedirects)
        self.assertIsNone(handler().redirect_request(None,None,302,"Found",{},"http://169.254.169.254/"))
        opener.open.assert_called_once()

    def test_unraid_notes_reject_untrusted_detail_hosts_before_fetch(self):
        src={"id":"unraid-preview-notes","kind":"unraid_notes","baseline":"7.4.0","channel":"preview","url":"https://docs.unraid.net/category/release-notes/"}
        fixture=b'<a href="https://evil.example/unraid-os/release-notes/7.5.0-rc1/">7.5.0-rc1</a><a href="//evil.example/unraid-os/release-notes/7.5.1-rc1/">7.5.1-rc1</a><a href="/unraid-os/release-notes/7.5.2-rc1/">7.5.2-rc1</a>'
        from unittest.mock import patch
        with patch.object(watch,"request",return_value=b"<p>6.18.70-Unraid</p>") as fetch:
            found=watch.normalize(src,fixture)
        self.assertEqual([x["id"] for x in found],["7.5.2-rc1"])
        fetch.assert_called_once_with("https://docs.unraid.net/unraid-os/release-notes/7.5.2-rc1/",allow_redirects=False)
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
