using UnityEditor;
using UnityEditor.TestTools.TestRunner.Api;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    public static class ProjectTestRunner
    {
        private static TestRunnerApi activeRunner;

        [MenuItem("Tools/MatsuMotoMeterAR/Run EditMode Tests")]
        public static void RunEditModeTests()
        {
            if (activeRunner != null)
            {
                Debug.LogWarning("[Tests] An EditMode test run is already active.");
                return;
            }

            activeRunner = ScriptableObject.CreateInstance<TestRunnerApi>();
            activeRunner.RegisterCallbacks(new ResultCallbacks());
            activeRunner.Execute(new ExecutionSettings(new Filter
            {
                testMode = TestMode.EditMode
            }));
            Debug.Log("[Tests] EditMode run started.");
        }

        private sealed class ResultCallbacks : ICallbacks
        {
            public void RunStarted(ITestAdaptor testsToRun)
            {
            }

            public void RunFinished(ITestResultAdaptor result)
            {
                Debug.Log(
                    $"[Tests] EditMode complete: " +
                    $"Passed={result.PassCount}, Failed={result.FailCount}, " +
                    $"Skipped={result.SkipCount}, Inconclusive={result.InconclusiveCount}.");
                activeRunner = null;
            }

            public void TestStarted(ITestAdaptor test)
            {
            }

            public void TestFinished(ITestResultAdaptor result)
            {
                if (result.TestStatus == TestStatus.Failed)
                {
                    Debug.LogError(
                        $"[Tests] Failed: {result.FullName}\n" +
                        $"{result.Message}\n{result.StackTrace}");
                }
            }
        }
    }
}
