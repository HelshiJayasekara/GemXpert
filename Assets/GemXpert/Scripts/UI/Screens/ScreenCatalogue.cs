using GemXpert.Core;

namespace GemXpert.UI
{
    /// <summary>Static descriptions of each studio area: hub tile text and the phase that delivers it.</summary>
    public static class ScreenCatalogue
    {
        public readonly struct Entry
        {
            public Entry(AppScreen screen, string title, string summary, int phase, string detail)
            {
                Screen = screen;
                Title = title;
                Summary = summary;
                Phase = phase;
                Detail = detail;
            }

            public AppScreen Screen { get; }
            public string Title { get; }
            public string Summary { get; }
            public int Phase { get; }
            public string Detail { get; }
        }

        public static readonly Entry[] HubEntries =
        {
            new Entry(AppScreen.RingSelection, "Ring Designs", "Solitaire, halo, three-stone, prong and bezel settings.", 3,
                "Browse the five ring settings, see each one on a display stand and choose one to customise."),
            new Entry(AppScreen.GemstoneSelection, "Gemstones", "Sapphires, ruby, emerald and diamond-style, in six cuts.", 3,
                "Choose the gemstone and cut. Only combinations the selected setting can hold are offered, and the reason is shown when one does not fit."),
            new Entry(AppScreen.Customization, "Customise", "Stone size and position, plus the metal of the band.", 3,
                "Adjust the length, width and seat position of the stone within the setting's limits, and switch between yellow, white and rose gold or silver."),
            new Entry(AppScreen.Inspection, "Inspect", "Wear the ring on your hand, then rotate, zoom and compare.", 4,
                "The ring is attached to your virtual ring finger. Rotate your hand, zoom in on the stone, reset the view or compare two designs side by side."),
            new Entry(AppScreen.DesignSummary, "Design Summary", "Review every choice and save the design.", 6,
                "A full specification of the current design (setting, stone, cut, dimensions, metal) with Save Design."),
            new Entry(AppScreen.SavedDesigns, "Saved Designs", "Reopen and compare designs you have saved.", 6,
                "Saved designs persist between sessions and can be restored or compared."),
        };

        public static readonly Entry DeviceEntry = new Entry(AppScreen.DeviceConnection, "Wearable Device",
            "Connect the GemXpert ESP32 ring controller.", 5,
            "Scan for and connect the ESP32 + IMU wearable over Bluetooth LE, calibrate it and view live orientation. " +
            "A built-in simulator lets everything work without the hardware.");

        public static bool TryGet(AppScreen screen, out Entry entry)
        {
            foreach (var e in HubEntries)
            {
                if (e.Screen == screen) { entry = e; return true; }
            }
            if (DeviceEntry.Screen == screen) { entry = DeviceEntry; return true; }
            entry = default;
            return false;
        }
    }
}
