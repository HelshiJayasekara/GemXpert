using System.Collections.Generic;
using System.IO;
using System.Linq;
using GemXpert.Core;
using GemXpert.Core.Catalogue;
using GemXpert.Interaction;
using GemXpert.UI;
using TMPro;
using Unity.XR.CoreUtils;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.XR;
using UnityEngine.Rendering;
using UnityEngine.XR.Interaction.Toolkit;
using UnityEngine.XR.Interaction.Toolkit.Locomotion.Teleportation;
using UnityEngine.XR.Interaction.Toolkit.UI;

namespace GemXpert.EditorTools
{
    /// <summary>
    /// Builds Scenes/MainShowroom/MainShowroom.unity from code so the scene is reproducible and reviewable.
    ///
    /// World layout (metres, user starts at the origin facing +Z):
    ///   room 12 (x) x 10 (z) x 3.6 (h), spanning z -4..6
    ///   main UI panel at (0, 1.42, 1.5)
    ///   five display stands on an arc (r = 3.6 m) - one per ring design in rings.json
    ///   GEMXPERT branding on the back wall (z = 6)
    ///
    /// Re-running the builder overwrites the scene (materials are updated in place).
    /// </summary>
    public static class ShowroomSceneBuilder
    {
        public const string ScenePath = "Assets/GemXpert/Scenes/MainShowroom/MainShowroom.unity";

        private const float RoomWidth = 12f;
        private const float RoomDepth = 10f;
        private const float RoomHeight = 3.6f;
        private const float RoomCenterZ = 1f;
        private const float StandArcRadius = 3.6f;
        private static readonly float[] StandAngles = { -64f, -32f, 0f, 32f, 64f };

        private static readonly Color Gold = new Color(0.902f, 0.788f, 0.514f);
        private static readonly Color Ivory = new Color(0.953f, 0.933f, 0.898f);
        private static readonly Color Muted = new Color(0.616f, 0.592f, 0.549f);

        [MenuItem(Bootstrap.GemXpertProjectSetup.BuildSceneMenu, priority = 30)]
        public static void Build()
        {
            if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;

            if (TMP_Settings.defaultFontAsset == null)
            {
                Debug.LogWarning("[GemXpert] TextMeshPro essentials are missing; 3D labels will be blank. " +
                                 "Run GemXpert > Setup > 3 - Import TextMeshPro Essentials, then rebuild.");
            }

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var mats = new ShowroomMaterials();

            var environment = new GameObject("Environment").transform;
            var floor = BuildRoom(environment, mats);
            BuildDisplayStands(environment, mats);
            BuildBranding(environment, mats);
            BuildLighting(environment);

            var origin = CreateRig(out var camera);
            ConfigureCamera(camera);
            var simulator = CreateSimulator();
            AddTeleportArea(floor);

            var systems = new GameObject("GemXpert Systems");
            systems.AddComponent<AppStateController>();
            systems.AddComponent<CatalogueService>();
            systems.AddComponent<XRCanvasSetup>();

            var eventSystem = new GameObject("EventSystem", typeof(EventSystem), typeof(XRUIInputModule));
            eventSystem.transform.SetParent(systems.transform, false);

            var panel = new GameObject("Main Panel");
            panel.transform.SetPositionAndRotation(new Vector3(0f, 1.42f, 1.5f), Quaternion.identity);
            var router = panel.AddComponent<ScreenRouter>();

            var desktop = origin.gameObject.AddComponent<DesktopPreviewController>();
            desktop.Configure(origin.transform, camera);
            desktop.enabled = false;

            var runMode = systems.AddComponent<RunModeController>();
            runMode.Configure(origin, simulator, desktop, router);

            GemXpertRenderSetup.EnsureFolder(Path.GetDirectoryName(ScenePath)?.Replace('\\', '/'));
            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene, ScenePath))
            {
                Debug.LogError("[GemXpert] Failed to save " + ScenePath);
                return;
            }
            AddToBuildSettings(ScenePath);
            Debug.Log($"[GemXpert] Showroom scene built: {ScenePath} (rig: {origin.name}, simulator: {(simulator ? simulator.name : "none")})");
        }

        // ------------------------------------------------------------------ room

        private static GameObject BuildRoom(Transform parent, ShowroomMaterials m)
        {
            var room = new GameObject("Room").transform;
            room.SetParent(parent, false);

            var halfW = RoomWidth / 2f;
            var zMin = RoomCenterZ - RoomDepth / 2f;
            var zMax = RoomCenterZ + RoomDepth / 2f;

            var floor = Box("Floor", room, new Vector3(0f, -0.05f, RoomCenterZ), new Vector3(RoomWidth, 0.1f, RoomDepth), m.Floor);
            Box("Ceiling", room, new Vector3(0f, RoomHeight + 0.05f, RoomCenterZ), new Vector3(RoomWidth, 0.1f, RoomDepth), m.Ceiling);
            Box("Wall_Back", room, new Vector3(0f, RoomHeight / 2f, zMax + 0.1f), new Vector3(RoomWidth + 0.4f, RoomHeight, 0.2f), m.Wall);
            Box("Wall_Front", room, new Vector3(0f, RoomHeight / 2f, zMin - 0.1f), new Vector3(RoomWidth + 0.4f, RoomHeight, 0.2f), m.Wall);
            Box("Wall_Left", room, new Vector3(-halfW - 0.1f, RoomHeight / 2f, RoomCenterZ), new Vector3(0.2f, RoomHeight, RoomDepth), m.Wall);
            Box("Wall_Right", room, new Vector3(halfW + 0.1f, RoomHeight / 2f, RoomCenterZ), new Vector3(0.2f, RoomHeight, RoomDepth), m.Wall);

            // Gold skirting, dado line and warm cove light along all four walls.
            var trims = new GameObject("Trim").transform;
            trims.SetParent(room, false);
            foreach (var (y, h, mat, label) in new[]
                     {
                         (0.06f, 0.12f, m.GoldTrim, "Skirting"),
                         (1.0f, 0.015f, m.GoldTrim, "Dado"),
                         (RoomHeight - 0.12f, 0.04f, m.CoveLight, "Cove"),
                     })
            {
                Box($"{label}_Back", trims, new Vector3(0f, y, zMax - 0.01f), new Vector3(RoomWidth, h, 0.02f), mat, false);
                Box($"{label}_Front", trims, new Vector3(0f, y, zMin + 0.01f), new Vector3(RoomWidth, h, 0.02f), mat, false);
                Box($"{label}_Left", trims, new Vector3(-halfW + 0.01f, y, RoomCenterZ), new Vector3(0.02f, h, RoomDepth), mat, false);
                Box($"{label}_Right", trims, new Vector3(halfW - 0.01f, y, RoomCenterZ), new Vector3(0.02f, h, RoomDepth), mat, false);
            }

            // Framed wall panels on the side walls.
            var panels = new GameObject("WallPanels").transform;
            panels.SetParent(room, false);
            for (var z = zMin + 2f; z <= zMax - 1.9f; z += 2f)
            {
                foreach (var side in new[] { -1f, 1f })
                {
                    var x = side * (halfW - 0.03f);
                    var center = new Vector3(x, 2.2f, z);
                    Box($"Panel_{(side < 0 ? "L" : "R")}_{z:0}", panels, center, new Vector3(0.04f, 2.0f, 1.5f), m.WallPanel, false);
                    // thin gold frame
                    var fx = x - side * 0.022f;
                    Box("FrameTop", panels, new Vector3(fx, 3.2f, z), new Vector3(0.01f, 0.012f, 1.5f), m.GoldTrim, false);
                    Box("FrameBottom", panels, new Vector3(fx, 1.2f, z), new Vector3(0.01f, 0.012f, 1.5f), m.GoldTrim, false);
                    Box("FrameNear", panels, new Vector3(fx, 2.2f, z - 0.75f), new Vector3(0.01f, 2.0f, 0.012f), m.GoldTrim, false);
                    Box("FrameFar", panels, new Vector3(fx, 2.2f, z + 0.75f), new Vector3(0.01f, 2.0f, 0.012f), m.GoldTrim, false);
                }
            }

            return floor;
        }

        // ------------------------------------------------------------------ display stands

        private static void BuildDisplayStands(Transform parent, ShowroomMaterials m)
        {
            var root = new GameObject("DisplayStands").transform;
            root.SetParent(parent, false);

            IReadOnlyList<RingDesignDefinition> rings;
            try
            {
                rings = CatalogueDatabase.LoadFromResources().Rings;
            }
            catch (System.Exception ex)
            {
                Debug.LogException(ex);
                rings = new List<RingDesignDefinition>();
            }

            for (var i = 0; i < StandAngles.Length; i++)
            {
                var rad = StandAngles[i] * Mathf.Deg2Rad;
                var pos = new Vector3(Mathf.Sin(rad), 0f, Mathf.Cos(rad)) * StandArcRadius;
                var toUser = new Vector3(-pos.x, 0f, -pos.z).normalized;
                var ring = i < rings.Count ? rings[i] : null;

                var stand = new GameObject(ring != null ? $"Stand_{ring.id}" : $"Stand_{i}").transform;
                stand.SetParent(root, false);
                stand.SetPositionAndRotation(pos, Quaternion.LookRotation(toUser, Vector3.up));

                Box("Plinth", stand, new Vector3(0f, 0.5f, 0f), new Vector3(0.44f, 1.0f, 0.44f), m.Lacquer);
                Box("GoldBase", stand, new Vector3(0f, 0.02f, 0f), new Vector3(0.48f, 0.04f, 0.48f), m.GoldTrim, false);
                Box("GoldCap", stand, new Vector3(0f, 1.01f, 0f), new Vector3(0.48f, 0.02f, 0.48f), m.GoldTrim, false);
                Box("VelvetPad", stand, new Vector3(0f, 1.035f, 0f), new Vector3(0.3f, 0.03f, 0.3f), m.Velvet, false);
                Box("GlassCase", stand, new Vector3(0f, 1.22f, 0f), new Vector3(0.42f, 0.36f, 0.42f), m.Glass, false, false);

                // Where the ring model is placed in Phase 3 (top of the velvet pad).
                var anchor = new GameObject("RingDisplayAnchor").transform;
                anchor.SetParent(stand, false);
                anchor.localPosition = new Vector3(0f, 1.07f, 0f);

                if (ring == null) continue;
                // Labels face the user (TextMeshPro reads correctly when looking along its +Z).
                var labelRot = Quaternion.Euler(0f, 180f, 0f);
                Label3D("Label_Name", stand, ring.displayName.ToUpperInvariant(), 0.42f, Gold,
                    new Vector3(0f, 0.86f, 0.222f), labelRot, new Vector2(0.42f, 0.06f), FontStyles.Bold, 4f);
                Label3D("Label_Style", stand, ring.settingStyle, 0.26f, Muted,
                    new Vector3(0f, 0.8f, 0.222f), labelRot, new Vector2(0.42f, 0.04f));
            }
        }

        // ------------------------------------------------------------------ branding

        private static void BuildBranding(Transform parent, ShowroomMaterials m)
        {
            var root = new GameObject("Branding").transform;
            root.SetParent(parent, false);
            var wallZ = RoomCenterZ + RoomDepth / 2f - 0.02f;

            Label3D("Brand_Name", root, "GEMXPERT", 4.2f, Gold, new Vector3(0f, 2.78f, wallZ), Quaternion.identity,
                new Vector2(5f, 0.5f), FontStyles.Bold, 24f);
            Box("Brand_Rule", root, new Vector3(0f, 2.47f, wallZ), new Vector3(2.4f, 0.01f, 0.01f), m.GoldGlow, false);
            Label3D("Brand_Tagline", root, "IMMERSIVE GEMSTONE & JEWELLERY STUDIO", 1.05f, Ivory,
                new Vector3(0f, 2.3f, wallZ), Quaternion.identity, new Vector2(5f, 0.2f), FontStyles.Normal, 12f);
        }

        // ------------------------------------------------------------------ lighting

        private static void BuildLighting(Transform parent)
        {
            var root = new GameObject("Lighting").transform;
            root.SetParent(parent, false);

            RenderSettings.skybox = null;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.17f, 0.155f, 0.14f);
            RenderSettings.ambientEquatorColor = new Color(0.10f, 0.09f, 0.085f);
            RenderSettings.ambientGroundColor = new Color(0.04f, 0.035f, 0.03f);
            RenderSettings.fog = false;

            var key = new GameObject("Key Light (fill)").AddComponent<Light>();
            key.transform.SetParent(root, false);
            key.type = LightType.Directional;
            key.color = new Color(1f, 0.95f, 0.88f);
            key.intensity = 0.35f;
            key.shadows = LightShadows.None;
            key.transform.rotation = Quaternion.Euler(52f, 25f, 0f);
            RenderSettings.sun = key;

            // One warm spotlight per stand. Shadows off: jewellery spotlights are about sparkle, not shadow.
            for (var i = 0; i < StandAngles.Length; i++)
            {
                var rad = StandAngles[i] * Mathf.Deg2Rad;
                var target = new Vector3(Mathf.Sin(rad) * StandArcRadius, 1.05f, Mathf.Cos(rad) * StandArcRadius);
                var spot = new GameObject($"Spot_Stand_{i}").AddComponent<Light>();
                spot.transform.SetParent(root, false);
                spot.type = LightType.Spot;
                spot.color = new Color(1f, 0.88f, 0.74f);
                spot.intensity = 6f;
                spot.range = 4f;
                spot.spotAngle = 26f;
                spot.innerSpotAngle = 12f;
                spot.shadows = LightShadows.None;
                spot.transform.position = target + new Vector3(0f, RoomHeight - 1.05f - 0.1f, 0f);
                spot.transform.rotation = Quaternion.LookRotation(Vector3.down, Vector3.forward);
            }

            // A single reflection probe, rendered once on load: enough for metal and gem reflections at low cost.
            var probe = new GameObject("Reflection Probe").AddComponent<ReflectionProbe>();
            probe.transform.SetParent(root, false);
            probe.transform.position = new Vector3(0f, 1.4f, RoomCenterZ);
            probe.size = new Vector3(RoomWidth, RoomHeight, RoomDepth);
            probe.mode = ReflectionProbeMode.Realtime;
            probe.refreshMode = ReflectionProbeRefreshMode.OnAwake;
            probe.timeSlicingMode = ReflectionProbeTimeSlicingMode.AllFacesAtOnce;
            probe.resolution = 256;
            probe.hdr = false;
            probe.boxProjection = true;
        }

        // ------------------------------------------------------------------ rig

        private static XROrigin CreateRig(out Camera camera)
        {
            var prefab = FindSamplePrefab("XR Origin (XR Rig)");
            XROrigin origin = null;
            if (prefab != null)
            {
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                instance.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                origin = instance.GetComponent<XROrigin>();
            }

            if (origin == null)
            {
                Debug.LogWarning("[GemXpert] XRI Starter Assets 'XR Origin (XR Rig)' not found. Building a minimal head-only rig. " +
                                 "Import the sample (GemXpert > Setup > 2) and rebuild for controllers, hands and locomotion.");
                origin = CreateMinimalRig();
            }

            camera = origin.Camera != null ? origin.Camera : origin.GetComponentInChildren<Camera>(true);
            return origin;
        }

        private static XROrigin CreateMinimalRig()
        {
            var root = new GameObject("XR Origin (GemXpert Minimal)");
            var origin = root.AddComponent<XROrigin>();
            var offset = new GameObject("Camera Offset");
            offset.transform.SetParent(root.transform, false);

            var camGo = new GameObject("Main Camera", typeof(Camera), typeof(AudioListener));
            camGo.tag = "MainCamera";
            camGo.transform.SetParent(offset.transform, false);
            camGo.transform.localPosition = new Vector3(0f, 1.6f, 0f);

            var driver = camGo.AddComponent<TrackedPoseDriver>();
            driver.positionInput = new InputActionProperty(new InputAction("Head Position", InputActionType.Value,
                "<XRHMD>/centerEyePosition", expectedControlType: "Vector3"));
            driver.rotationInput = new InputActionProperty(new InputAction("Head Rotation", InputActionType.Value,
                "<XRHMD>/centerEyeRotation", expectedControlType: "Quaternion"));

            origin.Origin = root;
            origin.CameraFloorOffsetObject = offset;
            origin.Camera = camGo.GetComponent<Camera>();
            return origin;
        }

        private static void ConfigureCamera(Camera camera)
        {
            if (camera == null) return;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = Color.black;
            camera.nearClipPlane = 0.01f; // jewellery is inspected a few centimetres from the eye
            camera.farClipPlane = 50f;
        }

        private static GameObject CreateSimulator()
        {
            var prefab = FindSamplePrefab("XR Device Simulator") ?? FindSamplePrefab("XR Interaction Simulator");
            if (prefab == null)
            {
                Debug.LogWarning("[GemXpert] XR Device Simulator prefab not found. Simulator run mode will be unavailable.");
                return null;
            }
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            instance.SetActive(false); // RunModeController activates it only in XRDeviceSimulator mode
            return instance;
        }

        private static void AddTeleportArea(GameObject floor)
        {
            var area = floor.AddComponent<TeleportationArea>();
            var teleportLayer = InteractionLayerMask.GetMask("Teleport");
            if (teleportLayer != 0)
            {
                area.interactionLayers = teleportLayer;
            }
            else
            {
                Debug.LogWarning("[GemXpert] Interaction layer 'Teleport' not defined; teleport area uses default layers.");
            }
        }

        private static GameObject FindSamplePrefab(string fileName)
        {
            var folders = AssetDatabase.IsValidFolder("Assets/Samples") ? new[] { "Assets/Samples" } : new[] { "Assets" };
            return AssetDatabase.FindAssets("t:Prefab", folders)
                .Select(AssetDatabase.GUIDToAssetPath)
                .Where(p => Path.GetFileNameWithoutExtension(p) == fileName)
                .OrderByDescending(p => p) // newest sample version folder first
                .Select(AssetDatabase.LoadAssetAtPath<GameObject>)
                .FirstOrDefault(go => go != null);
        }

        // ------------------------------------------------------------------ helpers

        private static GameObject Box(string name, Transform parent, Vector3 localPos, Vector3 size, Material mat,
            bool collider = true, bool isStatic = true)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPos;
            go.transform.localScale = size;
            go.GetComponent<MeshRenderer>().sharedMaterial = mat;
            if (!collider) Object.DestroyImmediate(go.GetComponent<Collider>());
            if (isStatic)
            {
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ReflectionProbeStatic);
            }
            return go;
        }

        private static TextMeshPro Label3D(string name, Transform parent, string text, float size, Color color,
            Vector3 localPos, Quaternion localRot, Vector2 rect, FontStyles style = FontStyles.Normal, float spacing = 0f)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPos;
            go.transform.localRotation = localRot;
            var tmp = go.AddComponent<TextMeshPro>();
            tmp.text = text;
            tmp.fontSize = size; // TextMeshPro (3D): fontSize 1 ~ 0.1 m line height
            tmp.color = color;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.fontStyle = style;
            tmp.characterSpacing = spacing;
            tmp.textWrappingMode = TextWrappingModes.NoWrap;
            tmp.rectTransform.sizeDelta = rect;
            return tmp;
        }

        private static void AddToBuildSettings(string path)
        {
            var scenes = EditorBuildSettings.scenes.ToList();
            scenes.RemoveAll(s => s.path == path);
            scenes.Insert(0, new EditorBuildSettingsScene(path, true));
            EditorBuildSettings.scenes = scenes.ToArray();
        }
    }
}
