using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace GemXpert.EditorTools
{
    /// <summary>
    /// Creates (once) and assigns a VR-oriented URP asset:
    /// 4x MSAA (essential for thin metal edges and gem facets in VR), no HDR (Quest bandwidth),
    /// short shadow distance, render scale 1. Re-running re-applies the settings without duplicating assets.
    /// </summary>
    public static class GemXpertRenderSetup
    {
        private const string Folder = "Assets/GemXpert/Settings/Rendering";
        private const string PipelinePath = Folder + "/GemXpert_URP.asset";
        private const string RendererPath = Folder + "/GemXpert_URP_Renderer.asset";

        [MenuItem(Bootstrap.GemXpertProjectSetup.ConfigureRenderingMenu, priority = 15)]
        public static void Configure()
        {
            EnsureFolder(Folder);

            var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(PipelinePath);
            if (pipeline == null)
            {
                var rendererData = ScriptableObject.CreateInstance<UniversalRendererData>();
                AssetDatabase.CreateAsset(rendererData, RendererPath);
                pipeline = UniversalRenderPipelineAsset.Create(rendererData);
                AssetDatabase.CreateAsset(pipeline, PipelinePath);
                Debug.Log("[GemXpert Setup] Created URP asset at " + PipelinePath);
            }

            pipeline.msaaSampleCount = 4;
            pipeline.renderScale = 1f;
            pipeline.supportsHDR = false;
            pipeline.shadowDistance = 8f;
            EditorUtility.SetDirty(pipeline);

            GraphicsSettings.defaultRenderPipeline = pipeline;
            var current = QualitySettings.GetQualityLevel();
            for (var i = 0; i < QualitySettings.names.Length; i++)
            {
                QualitySettings.SetQualityLevel(i, false);
                QualitySettings.renderPipeline = pipeline;
            }
            QualitySettings.SetQualityLevel(current, false);

            PlayerSettings.colorSpace = ColorSpace.Linear;
            AssetDatabase.SaveAssets();
            Debug.Log("[GemXpert Setup] URP assigned to Graphics settings and all quality levels.");
        }

        public static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            var parent = Path.GetDirectoryName(path)?.Replace('\\', '/');
            if (!string.IsNullOrEmpty(parent)) EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }
    }
}
