using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.PackageManager;
using UnityEditor.PackageManager.Requests;
using UnityEngine;
using PackageSample = UnityEditor.PackageManager.UI.Sample;

namespace GemXpert.EditorTools.Bootstrap
{
    /// <summary>
    /// One-click (or batch-mode) project setup. Every step is idempotent: it checks what is already
    /// done and only does the rest, so it is safe to run repeatedly.
    ///
    ///   1. Install required Unity packages (editor-recommended versions).
    ///   2. Import XR Interaction Toolkit samples (Starter Assets rig, XR Device Simulator).
    ///   3. Import TextMeshPro essential resources (default SDF font).
    ///   4. Player settings: Input System active, Linear colour space, product name.
    ///   5. Configure URP           (menu item in GemXpert.Editor – compiles once URP + XRI exist).
    ///   6. Build the showroom scene (menu item in GemXpert.Editor).
    ///
    /// Batch mode (no -quit; the method exits the editor itself):
    ///   Unity -batchmode -projectPath &lt;repo&gt; -executeMethod GemXpert.EditorTools.Bootstrap.GemXpertProjectSetup.RunFullSetupBatch -logFile -
    /// This bootstrap assembly has no package references, so it compiles in a brand-new empty project.
    /// </summary>
    [InitializeOnLoad]
    public static class GemXpertProjectSetup
    {
        public static readonly string[] RequiredPackages =
        {
            "com.unity.render-pipelines.universal",
            "com.unity.inputsystem",
            "com.unity.xr.management",
            "com.unity.xr.openxr",
            "com.unity.xr.interaction.toolkit",
            "com.unity.xr.hands",
            "com.unity.ugui",
            "com.unity.test-framework",
        };

        private const string XriPackage = "com.unity.xr.interaction.toolkit";
        private static readonly string[] XriSamples = { "Starter Assets", "XR Device Simulator" };

        public const string ConfigureRenderingMenu = "GemXpert/Setup/5 - Configure Rendering (URP)";
        public const string BuildSceneMenu = "GemXpert/Build/Main Showroom Scene";

        private const string RunningKey = "GemXpert.Setup.Running";
        private const string BatchKey = "GemXpert.Setup.Batch";
        private const string StartedKey = "GemXpert.Setup.StartedUtc";
        private const double BatchTimeoutMinutes = 40;

        private static ListRequest _listRequest;
        private static AddAndRemoveRequest _addRequest;
        private static bool _continueScheduled;

        static GemXpertProjectSetup()
        {
            // Resume after the domain reload that follows package installs / sample imports.
            if (SessionState.GetBool(RunningKey, false)) ScheduleContinue();
        }

        // ------------------------------------------------------------------ menu entry points

        [MenuItem("GemXpert/Setup/Run Full Setup", priority = 0)]
        public static void RunFullSetup() => Begin(batch: false);

        public static void RunFullSetupBatch() => Begin(batch: true);

        [MenuItem("GemXpert/Setup/1 - Install Required Packages", priority = 11)]
        public static void InstallPackagesOnly() => StartPackageInstall(null);

        [MenuItem("GemXpert/Setup/2 - Import XRI Samples", priority = 12)]
        public static void ImportSamplesMenu() => ImportXriSamples();

        [MenuItem("GemXpert/Setup/3 - Import TextMeshPro Essentials", priority = 13)]
        public static void ImportTmpMenu() => ImportTmpEssentials();

        [MenuItem("GemXpert/Setup/4 - Apply Player Settings", priority = 14)]
        public static void PlayerSettingsMenu() => ApplyPlayerSettings();

        // ------------------------------------------------------------------ orchestration

        private static void Begin(bool batch)
        {
            Log("Full setup started.");
            SessionState.SetBool(RunningKey, true);
            SessionState.SetBool(BatchKey, batch);
            SessionState.SetString(StartedKey, DateTime.UtcNow.ToString("o"));
            ScheduleContinue();
        }

        private static void ScheduleContinue()
        {
            if (_continueScheduled) return;
            _continueScheduled = true;
            EditorApplication.update += ContinueWhenReady;
        }

        private static void ContinueWhenReady()
        {
            if (EditorApplication.isCompiling || EditorApplication.isUpdating) return;
            if (_listRequest != null || _addRequest != null) return; // package operation in flight

            if (SessionState.GetBool(BatchKey, false) && TimedOut())
            {
                Fail("Setup timed out.");
                return;
            }

            EditorApplication.update -= ContinueWhenReady;
            _continueScheduled = false;

            try
            {
                Step();
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
                Fail("Setup stopped because of the exception above.");
            }
        }

        /// <summary>Runs the first unfinished step. Steps that trigger reloads/async work return early.</summary>
        private static void Step()
        {
            // 1. Packages
            if (_installedPackages == null)
            {
                StartPackageList();
                return;
            }
            var missing = RequiredPackages.Where(p => !_installedPackages.Contains(p)).ToArray();
            if (missing.Length > 0)
            {
                StartPackageInstall(missing);
                return;
            }

            // 2. XRI samples (needs XRI installed)
            if (ImportXriSamples())
            {
                AssetDatabase.Refresh();
                ScheduleContinue();
                return;
            }

            // 3. TMP essentials
            if (ImportTmpEssentials())
            {
                ScheduleContinue();
                return;
            }

            // 4. Player settings
            var restartNeeded = ApplyPlayerSettings();

            // 5 + 6. Steps implemented in GemXpert.Editor (compiled only when URP + XRI are present).
            // ExecuteMenuItem returns false when the menu does not exist (i.e. that assembly did not compile).
            if (!EditorApplication.ExecuteMenuItem(ConfigureRenderingMenu) ||
                !EditorApplication.ExecuteMenuItem(BuildSceneMenu))
            {
                Fail("GemXpert.Editor menu items are not available. Check the Console for compile errors " +
                     "(GemXpert.Editor compiles only after URP and XR Interaction Toolkit are installed).");
                return;
            }

            Finish(restartNeeded);
        }

        // ------------------------------------------------------------------ 1. packages

        private static HashSet<string> _installedPackages;

        private static void StartPackageList()
        {
            Log("Reading installed packages...");
            _listRequest = Client.List(true, false);
            EditorApplication.update += PollList;
        }

        private static void PollList()
        {
            if (_listRequest == null || !_listRequest.IsCompleted) return;
            EditorApplication.update -= PollList;

            if (_listRequest.Status == StatusCode.Success)
            {
                _installedPackages = new HashSet<string>(_listRequest.Result.Select(p => p.name));
                _listRequest = null;
                ScheduleContinue();
            }
            else
            {
                var error = _listRequest.Error?.message;
                _listRequest = null;
                Fail("Could not list packages: " + error);
            }
        }

        private static void StartPackageInstall(string[] packages)
        {
            if (packages == null)
            {
                packages = RequiredPackages;
            }

            Log("Installing packages: " + string.Join(", ", packages));
            _addRequest = Client.AddAndRemove(packages, null);
            EditorApplication.update += PollAdd;
        }

        private static void PollAdd()
        {
            if (_addRequest == null || !_addRequest.IsCompleted) return;
            EditorApplication.update -= PollAdd;

            var ok = _addRequest.Status == StatusCode.Success;
            var error = _addRequest.Error?.message;
            _addRequest = null;

            if (!ok)
            {
                Fail("Package install failed: " + error);
                return;
            }

            Log("Packages installed. Waiting for compilation/domain reload...");
            _installedPackages = null; // re-list after the reload
            if (SessionState.GetBool(RunningKey, false)) ScheduleContinue();
        }

        // ------------------------------------------------------------------ 2. samples

        /// <summary>Imports missing XRI samples. Returns true if an import was started.</summary>
        public static bool ImportXriSamples()
        {
            var samples = PackageSample.FindByPackage(XriPackage, null)?.ToList() ?? new List<PackageSample>();
            if (samples.Count == 0)
            {
                Log("XR Interaction Toolkit samples not found (is the package installed?).");
                return false;
            }

            var imported = false;
            foreach (var wanted in XriSamples)
            {
                var matches = samples.Where(s => s.displayName == wanted).ToList();
                if (matches.Count == 0)
                {
                    Log($"XRI sample '{wanted}' is not in this XRI version. Available: " +
                        string.Join(", ", samples.Select(s => s.displayName)));
                    continue;
                }
                var sample = matches[0];
                if (sample.isImported) continue;

                // Never retry the same sample in one editor session (prevents an endless import loop).
                var attemptKey = "GemXpert.Setup.SampleAttempted." + wanted;
                if (SessionState.GetBool(attemptKey, false))
                {
                    Debug.LogWarning($"[GemXpert Setup] Sample '{wanted}' still reports not imported after an import attempt. " +
                                     "Import it manually from Package Manager > XR Interaction Toolkit > Samples.");
                    continue;
                }
                SessionState.SetBool(attemptKey, true);

                Log($"Importing XRI sample '{wanted}'...");
                if (sample.Import(PackageSample.ImportOptions.HideImportWindow | PackageSample.ImportOptions.OverridePreviousImports))
                {
                    imported = true;
                }
                else
                {
                    Debug.LogWarning($"[GemXpert Setup] Importing sample '{wanted}' failed.");
                }
            }
            return imported;
        }

        // ------------------------------------------------------------------ 3. TextMeshPro

        /// <summary>Imports TMP Essential Resources if missing. Returns true if an import was started.</summary>
        public static bool ImportTmpEssentials()
        {
            if (AssetDatabase.FindAssets("t:TMP_Settings").Length > 0 || Directory.Exists("Assets/TextMesh Pro"))
            {
                return false;
            }

            foreach (var packageDir in new[] { "Packages/com.unity.ugui", "Packages/com.unity.textmeshpro" })
            {
                var full = Path.GetFullPath(packageDir);
                if (!Directory.Exists(full)) continue;
                var unityPackage = Directory.GetFiles(full, "TMP Essential Resources.unitypackage", SearchOption.AllDirectories).FirstOrDefault();
                if (unityPackage == null) continue;

                Log("Importing TextMeshPro Essential Resources from " + unityPackage);
                AssetDatabase.ImportPackage(unityPackage, false);
                return true;
            }

            Debug.LogWarning("[GemXpert Setup] TMP Essential Resources package not found. " +
                             "Import it manually: Window > TextMeshPro > Import TMP Essential Resources.");
            return false;
        }

        // ------------------------------------------------------------------ 4. player settings

        /// <summary>Returns true if a setting that needs an editor restart was changed.</summary>
        public static bool ApplyPlayerSettings()
        {
            PlayerSettings.companyName = "GemXpert";
            PlayerSettings.productName = "GemXpert";
            if (PlayerSettings.colorSpace != ColorSpace.Linear) PlayerSettings.colorSpace = ColorSpace.Linear;

            // activeInputHandler: 0 = legacy Input Manager, 1 = Input System package, 2 = both.
            var restart = false;
            var playerSettings = Unsupported.GetSerializedAssetInterfaceSingleton("PlayerSettings");
            if (playerSettings != null)
            {
                var so = new SerializedObject(playerSettings);
                var handler = so.FindProperty("activeInputHandler");
                if (handler != null && handler.intValue != 1)
                {
                    handler.intValue = 1;
                    so.ApplyModifiedProperties();
                    restart = true;
                    Log("Active input handling set to 'Input System Package'. Restart the editor for it to take effect.");
                }
            }
            AssetDatabase.SaveAssets();
            return restart;
        }

        // ------------------------------------------------------------------ helpers

        private static bool TimedOut()
        {
            var started = SessionState.GetString(StartedKey, "");
            return DateTime.TryParse(started, null, System.Globalization.DateTimeStyles.RoundtripKind, out var t)
                   && (DateTime.UtcNow - t).TotalMinutes > BatchTimeoutMinutes;
        }

        private static void Finish(bool restartNeeded)
        {
            SessionState.SetBool(RunningKey, false);
            Log("Full setup complete." + (restartNeeded ? " RESTART the editor before entering Play mode." : ""));
            if (SessionState.GetBool(BatchKey, false)) EditorApplication.Exit(0);
        }

        private static void Fail(string message)
        {
            SessionState.SetBool(RunningKey, false);
            Debug.LogError("[GemXpert Setup] " + message);
            if (SessionState.GetBool(BatchKey, false)) EditorApplication.Exit(1);
        }

        private static void Log(string message) => Debug.Log("[GemXpert Setup] " + message);
    }
}
