using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal sealed class ReleaseSecurityValidator : IPreprocessBuildWithReport
    {
        private const string DevAgentSettingsPath =
            "Assets/Resources/DevAgentSettings.asset";

        public int callbackOrder => -100;

        [MenuItem("Tools/MatsuMotoMeterAR/Validate Release Security")]
        private static void ValidateFromMenu()
        {
            Validate();
            Debug.Log("Release security validation passed.");
        }

        public void OnPreprocessBuild(BuildReport report)
        {
            try
            {
                Validate();
            }
            catch (Exception exception)
            {
                throw new BuildFailedException(
                    $"Release security validation failed: {exception.Message}");
            }
        }

        private static void Validate()
        {
            if (!File.Exists(DevAgentSettingsPath))
                return;

            throw new InvalidOperationException(
                $"{DevAgentSettingsPath} exists. Meta XR can inject a newly generated " +
                "Agent Bridge token into this Resources asset during preprocessing. " +
                "Remove the asset before building a distributable APK.");
        }
    }
}
