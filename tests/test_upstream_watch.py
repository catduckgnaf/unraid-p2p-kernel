import importlib.util, json, sys, unittest
from pathlib import Path

SCRIPT=Path(__file__).parents[1]/"scripts"/"upstream_watch.py"
spec=importlib.util.spec_from_file_location("watch",SCRIPT); watch=importlib.util.module_from_spec(spec); sys.modules[spec.name]=watch; spec.loader.exec_module(watch)

class WatchTests(unittest.TestCase):
    def test_relevant_commit_filter_excludes_noise_and_keeps_p2pdma(self):
        source={"id":"linux-mainline-p2pdma","kind":"github_commit"}
        raw=json.dumps([
          {"sha":"a"*40,"html_url":"https://github.com/a","commit":{"message":"PCI/P2PDMA: support Intel Xeon"}},
          {"sha":"b"*40,"html_url":"https://github.com/b","commit":{"message":"docs: fix typo"}}
        ]).encode()
        found=[x for x in watch.normalize(source,raw) if watch.relevant(x,source)]
        self.assertEqual([x["id"] for x in found],["a"*40])
    def test_deterministic_key_and_dedupe(self):
        x=watch.item("linux-mainline-p2pdma","abc","P2PDMA change","https://example.test")
        self.assertEqual(watch.key(x),watch.key(dict(x)))
        self.assertEqual(len({watch.key(x):x for x in [x,x]}),1)
    def test_digest_grouping_is_daily_and_deterministic(self):
        # Day-keyed digests coalesce multiple qualifying updates into one alert per source.
        from datetime import datetime, timezone
        day=datetime.now(timezone.utc).strftime("%Y-%m-%d")
        def digest(ids): return watch.hashlib.sha256(("source\\0"+day+"\\0"+"\\0".join(sorted(ids))).encode()).hexdigest()[:20]
        self.assertEqual(digest(["a","b"]),digest(["b","a"]))
        self.assertNotEqual(digest(["a","b"]),digest(["a"]))

    def test_unraid_stable_known_update_is_not_hidden_by_first_run_baseline(self):
        src={"id":"unraid-stable-notes","kind":"unraid_notes","baseline":"7.4.0","channel":"stable"}
        fixture='''<ul><li><a href="https://docs.unraid.net/unraid-os/release-notes/7.4.1/">7.4.1</a></li><li><a href="/unraid-os/release-notes/7.4.0/">7.4.0</a></li><li><a href="/unraid-os/release-notes/7.5.0-rc1/">7.5.0-rc1</a></li></ul>'''.encode()
        found=watch.normalize(src,fixture)
        self.assertEqual([(x["id"],x["status"]) for x in found],[("7.4.1","released")])
    def test_preview_is_separate_and_kernel_candidate_status_not_release(self):
        src={"id":"unraid-preview-notes","kind":"unraid_notes","baseline":"7.4.0","channel":"preview"}
        fixture=b'<a href="/unraid-os/release-notes/7.5.0-rc1/">7.5.0-rc1</a>'
        found=watch.normalize(src,fixture)
        self.assertEqual(found[0]["status"],"preview")
        self.assertEqual(found[0]["source"],"unraid-preview-notes")
    def test_kernel_versions_above_build_baseline_only(self):
        src={"id":"linux-kernel-releases","kind":"kernel_releases"}
        raw=json.dumps({"releases":[{"version":"6.18.60","moniker":"longterm"},{"version":"6.18.65","moniker":"longterm","tarball":"https://kernel.org/6.18.65"},{"version":"7.4-rc4","moniker":"mainline"}]}).encode()
        self.assertEqual([x["id"] for x in watch.normalize(src,raw)],["6.18.65"])
    def test_nvidia_prereleases_excluded(self):
        src={"id":"nvidia-open-modules","kind":"github_releases"}
        raw=json.dumps([{"tag_name":"580.196.11","name":"580.196.11","html_url":"https://github.com/nvidia/580","draft":False,"prerelease":False},{"tag_name":"beta","prerelease":True}]).encode()
        self.assertEqual([x["id"] for x in watch.normalize(src,raw)],["580.196.11"])

if __name__=="__main__": unittest.main()
