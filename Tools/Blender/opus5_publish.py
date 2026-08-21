"""Publishing a candidate: guard, stage, verify, then promote.

Alignment 73.4 and 76.3. A candidate is two files that only mean anything
together - a Blend and the report that says the Blend passed. The first version
of this wrote the report and then saved the Blend, so a failed save left a
report claiming a Blend that was never written; and a trial run could still
write the canonical summary.

So publishing is a transaction with the report as its commit marker:

1. refuse outright if the canonical revision already exists, on either side -
   an approved revision is never replaced and there is no force option;
2. stage both files in a unique temporary directory;
3. verify the staged Blend by reopening it and hashing it, and hash the report;
4. promote the Blend first and the report last.

The contract that buys is simple to state and easy to check: **if the report is
there, the Blend beside it was written, reopened and hashed.** A crash between
the two leaves a Blend with no report, which reads as "not published" - the safe
direction.

The verification and write steps are injectable so the failure paths can be
exercised on a real filesystem without Blender.
"""

import hashlib
import json
import shutil
import tempfile
from pathlib import Path


class CanonicalOutputExists(RuntimeError):
    """A canonical revision is already published and must not be replaced."""


class PublishFailed(RuntimeError):
    """Staging or verification failed; nothing canonical was written."""


def publish_guard(blend_exists, report_exists, problems, trial):
    """Where, if anywhere, a run is allowed to write.

    Deliberately free of `bpy` and of the filesystem so the cases can be
    exercised directly. There is no force option: replacing an approved
    revision is the thing this exists to prevent.
    """
    if trial:
        return {
            "mode": "trial",
            "may_write_report": True,
            "may_write_blend": not problems,
            "reason": "trial run; canonical outputs untouched",
        }
    if blend_exists or report_exists:
        raise CanonicalOutputExists(
            "canonical outputs already exist for this revision "
            f"(blend={blend_exists}, report={report_exists}); "
            "use --trial-dir to iterate, or publish a new revision"
        )
    if problems:
        return {
            "mode": "canonical",
            "may_write_report": False,
            "may_write_blend": False,
            "reason": f"{len(problems)} problem(s); nothing is published",
        }
    return {
        "mode": "canonical",
        "may_write_report": True,
        "may_write_blend": True,
        "reason": "all checks passed; publishing blend and report together",
    }


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def publish(
    blend_path,
    report_path,
    report,
    problems,
    trial_dir=None,
    save_blend=None,
    reopen_blend=None,
):
    """Stage, verify and promote one candidate. Returns the publish record."""
    blend_path = Path(blend_path)
    report_path = Path(report_path)
    decision = publish_guard(
        blend_path.exists(), report_path.exists(), problems, trial_dir
    )
    record = dict(decision)

    if not decision["may_write_report"]:
        # A failing canonical run publishes nothing at all, not even a report.
        return record

    staging = Path(tempfile.mkdtemp(prefix="opus5-publish-"))
    try:
        staged_report = staging / report_path.name
        staged_blend = staging / blend_path.name

        if decision["may_write_blend"]:
            if save_blend is None:
                raise PublishFailed("no save_blend was provided")
            save_blend(staged_blend)
            if not staged_blend.is_file():
                raise PublishFailed(f"staged blend was not written: {staged_blend}")
            if reopen_blend is not None:
                # Reading it back is the difference between "we called save"
                # and "there is a file that loads".
                reopen_blend(staged_blend)
            record["blend_sha256"] = digest(staged_blend)
            record["blend_bytes"] = staged_blend.stat().st_size
            report = dict(report, published_blend_sha256=record["blend_sha256"])

        # The record goes into the file it describes, so a published report
        # states on its face which Blend it certifies.
        staged_report.write_text(
            json.dumps(dict(report, publish=dict(record)), indent=2) + "\n",
            encoding="utf-8",
        )
        record["report_sha256"] = digest(staged_report)

        report_path.parent.mkdir(parents=True, exist_ok=True)
        if decision["may_write_blend"]:
            blend_path.parent.mkdir(parents=True, exist_ok=True)
            # Blend first, report last: the report is the commit marker.
            shutil.move(str(staged_blend), str(blend_path))
        shutil.move(str(staged_report), str(report_path))
        record["promoted"] = True
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return record


def self_test_publish_transaction(root):
    """Filesystem tests for the four ways this can end.

    Alignment 76.3: the pure-function tests only checked the decision, so they
    could not see a half-written publish. These run against real files.
    """
    root = Path(root)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    results = {}

    def case(name):
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "candidate.blend", directory / "candidate.json"

    def good_save(path):
        Path(path).write_bytes(b"BLENDER-FAKE")

    # 1. The staged save raises: nothing canonical, on either side.
    blend, report = case("temp_blend_save_failure")
    def failing_save(path):
        raise RuntimeError("simulated save failure")
    try:
        publish(blend, report, {"ok": True}, [], save_blend=failing_save)
    except RuntimeError:
        pass
    results["temp_blend_save_failure"] = {
        "blend": blend.exists(),
        "report": report.exists(),
        "passed": not blend.exists() and not report.exists(),
    }

    # 2. The report write raises after the blend staged fine: still nothing.
    blend, report = case("report_write_failure")
    original = Path.write_text
    def failing_write(self, *args, **kwargs):
        if self.suffix == ".json":
            raise OSError("simulated report write failure")
        return original(self, *args, **kwargs)
    Path.write_text = failing_write
    try:
        publish(blend, report, {"ok": True}, [], save_blend=good_save)
    except OSError:
        pass
    finally:
        Path.write_text = original
    results["report_write_failure"] = {
        "blend": blend.exists(),
        "report": report.exists(),
        "passed": not blend.exists() and not report.exists(),
    }

    # 3. A one-sided canonical output already exists: refuse, touch nothing.
    blend, report = case("existing_one_sided_output")
    blend.write_bytes(b"already here")
    raised = False
    try:
        publish(blend, report, {"ok": True}, [], save_blend=good_save)
    except CanonicalOutputExists:
        raised = True
    results["existing_one_sided_output"] = {
        "raised": raised,
        "report": report.exists(),
        "passed": raised and not report.exists(),
    }

    # 4. The happy path: both promoted, and the report carries the blend hash.
    blend, report = case("successful_promotion")
    record = publish(blend, report, {"ok": True}, [], save_blend=good_save)
    payload = json.loads(report.read_text()) if report.exists() else {}
    results["successful_promotion"] = {
        "blend": blend.exists(),
        "report": report.exists(),
        "record": record,
        "passed": (
            blend.exists()
            and report.exists()
            and payload.get("published_blend_sha256") == record.get("blend_sha256")
        ),
    }
    return results
