using System;
using UnityEngine;

namespace GemXpert.Core.Catalogue
{
    /// <summary>
    /// Loads the JSON catalogue once at startup and exposes it to every other system.
    /// Validation problems are logged loudly instead of being ignored.
    /// </summary>
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(-900)]
    public sealed class CatalogueService : MonoBehaviour
    {
        public static CatalogueService Instance { get; private set; }

        public CatalogueDatabase Database { get; private set; }
        public bool IsValid { get; private set; }

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                enabled = false;
                return;
            }
            Instance = this;

            try
            {
                Database = CatalogueDatabase.LoadFromResources();
                var errors = Database.Validate();
                IsValid = errors.Count == 0;
                if (IsValid)
                {
                    Debug.Log($"[GemXpert] Catalogue loaded: {Database.Rings.Count} rings, {Database.Gemstones.Count} gemstones, " +
                              $"{Database.Shapes.Count} shapes, {Database.Metals.Count} metals.");
                }
                else
                {
                    Debug.LogError("[GemXpert] Catalogue has problems:\n - " + string.Join("\n - ", errors));
                }
            }
            catch (Exception ex)
            {
                IsValid = false;
                Database = new CatalogueDatabase(null, null, null, null);
                Debug.LogException(ex);
            }
        }

        private void OnDestroy()
        {
            if (Instance == this) Instance = null;
        }
    }
}
