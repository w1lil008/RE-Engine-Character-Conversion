# Grace live capture — read-only

The v7 probe has been tested live on the installed build. No additional runtime mod package is required. Keep the working Bela character
mod installed. Leave every prepared animation resource outside RE9.

1. Close any RE9 session left open from the saved autonomous capture, then load Grace in a quiet area using the existing working character mod.
2. Open REFramework, expand **ScriptRunner**, click **Run script**, and open:
   `<LOCAL_PROJECT_ROOT>\scripts\runtime\bela_binding_probe_v7.lua`.
3. Under **Script Generated UI**, expand **Bela D7 - read-only binding capture**.
   Click **Find Grace candidate**. The verified cp_A100 controller is selected automatically; capture controls are above the optional object list.
4. If automatic selection fails, enable **Show manual object selection**, expand **cp_A100** and click **Watch as body**.
   In the atrium this was entry **412**; Guard Office used **409**, both reporting **80** joints.
   Indices can change after reloading: identify the prefab, not that number.
   Do not select the `Shadow` objects just because they report 611 joints.
5. Enter the room, camera and weapon context, then confirm the Grace checkbox.
   The observed scene was Main Care centre atrium / third person / Requiem.
6. Click **Start capture**. Mark and perform these actions, about five seconds each (wait until post-load weapon handling finishes first):
   **idle → walk → idle_after_walk → aim → idle_after_aim**.
   Use the **Mark walk**, **Mark idle_after_walk**, **Mark aim**, and **Mark idle_after_aim** buttons before each action, closing the overlay for gameplay input. The optional hotkeys below avoid repeatedly opening the overlay.
7. Click **Stop and save**. Check that the panel displays a saved filename.
   Tell Codex the capture is finished; it can read the file directly.

Optional: enable **F6 start / F7 next action / F8 save**, then close the REFramework
overlay so gameplay input is available. Press F7 just before each phase change;
holding the key produces one marker. Use these keys only if they do not conflict
with your bindings. No key interception or game key remapping occurs.

Captures are new JSON files inside:
`<RE9_INSTALL_DIR>\reframework\data\bela_d2\`.
The folder name is shared by D2–D7. Older captures are retained.

If discovery fails, use **Save discovery diagnostics** instead; it works with zero
samples and no checkbox. If saving fails, use **Retry save**. Unsaved samples are
retained and cannot be cleared/replaced by another capture. Missing APIs are
recorded rather than treated as successful observations. Sampling stops after
120 seconds, 600 samples, or three successive samples above 20 ms.

**Clear saved capture / release Lua references** stops retaining selected objects.
Closing RE9 unloads the manually loaded script. Nothing was installed in autorun.
Do not reset all REFramework scripts; unrelated working mods may depend on them.

Offline preparation preview: run `scripts\Prepare_Runtime_Capture.ps1` from the
workspace. It reports paths, fingerprints and conflicts; it installs nothing.
To analyze the most recent saved diagnostic, run it with **-AnalyzeLatest**.
The analyzed report goes under `reports\runtime_preparation_v0.2.0\captures\`;
the raw reference is copied under `build\animation_v0.2.0\runtime_hardening\captures\`.

Native playback remains separately gated. Capturing the current game does not
authorize loading or playing the converted animation.

