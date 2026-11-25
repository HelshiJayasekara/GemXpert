using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace GemXpert.EditorTools
{
    /// <summary>
    /// Creates or updates the showroom's URP Lit materials as assets in Materials/Environment.
    /// Palette: black lacquer, charcoal walls, polished dark stone floor, champagne-gold trim, burgundy velvet.
    /// </summary>
    public sealed class ShowroomMaterials
    {
        private const string Folder = "Assets/GemXpert/Materials/Environment";

        public Material Floor { get; }
        public Material Wall { get; }
        public Material WallPanel { get; }
        public Material Ceiling { get; }
        public Material GoldTrim { get; }
        public Material GoldGlow { get; }
        public Material CoveLight { get; }
        public Material Lacquer { get; }
        public Material Velvet { get; }
        public Material Glass { get; }

        public ShowroomMaterials()
        {
            GemXpertRenderSetup.EnsureFolder(Folder);
            Floor = Lit("Showroom_Floor_PolishedStone", Hex("#121215"), 0f, 0.82f);
            Wall = Lit("Showroom_Wall_Charcoal", Hex("#1C1A20"), 0f, 0.22f);
            WallPanel = Lit("Showroom_Wall_Panel", Hex("#25222B"), 0f, 0.35f);
            Ceiling = Lit("Showroom_Ceiling", Hex("#0E0E11"), 0f, 0.1f);
            GoldTrim = Lit("Showroom_GoldTrim", Hex("#C9A45C"), 1f, 0.78f);
            GoldGlow = Lit("Showroom_GoldGlow", Hex("#E6C983"), 0f, 0.5f, Hex("#C9A45C") * 1.6f);
            CoveLight = Lit("Showroom_CoveLight", Hex("#FFE8C8"), 0f, 0.5f, Hex("#FFD9A8") * 1.2f);
            Lacquer = Lit("Showroom_BlackLacquer", Hex("#0B0B0D"), 0f, 0.9f);
            Velvet = Lit("Showroom_Velvet_Burgundy", Hex("#3A0F1E"), 0f, 0.05f);
            Glass = Lit("Showroom_Glass", new Color(0.9f, 0.95f, 1f, 0.1f), 0f, 0.96f, null, true);
            AssetDatabase.SaveAssets();
        }

        private static Material Lit(string name, Color color, float metallic, float smoothness, Color? emission = null, bool transparent = false)
        {
            var path = $"{Folder}/{name}.mat";
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null)
            {
                Debug.LogError("[GemXpert] URP Lit shader not found. Run GemXpert > Setup > Run Full Setup first.");
                shader = Shader.Find("Standard");
            }

            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(shader);
                AssetDatabase.CreateAsset(mat, path);
            }
            else
            {
                mat.shader = shader;
            }

            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Metallic", metallic);
            mat.SetFloat("_Smoothness", smoothness);

            if (emission.HasValue)
            {
                mat.EnableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", emission.Value);
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }
            else
            {
                mat.DisableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", Color.black);
            }

            if (transparent)
            {
                mat.SetFloat("_Surface", 1f); // Transparent
                mat.SetFloat("_Blend", 0f);   // Alpha
                mat.SetOverrideTag("RenderType", "Transparent");
                mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                mat.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                mat.SetFloat("_ZWrite", 0f);
                mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                mat.renderQueue = (int)RenderQueue.Transparent;
            }

            EditorUtility.SetDirty(mat);
            return mat;
        }

        private static Color Hex(string hex)
        {
            ColorUtility.TryParseHtmlString(hex, out var c);
            return c;
        }
    }
}
