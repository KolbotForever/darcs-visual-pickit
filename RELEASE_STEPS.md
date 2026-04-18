## Darc's Visual Pickit Release Steps

This folder keeps the version in the folder name.
Internal filenames stay stable.

### For the next release

1. Copy this whole folder and rename the copy to the next version folder.
Example: `Darc's Visual Pickit V0.2.03`

2. Open `release_metadata.py` in the new folder and update:
   - `APP_VERSION`
   - `PUBLIC_RELEASE_VERSION`
   - `APP_BUILD_DATE`

3. Open `GITHUB_RELEASE.md` in the new folder and update:
   - title
   - highlights
   - fixes
   - release asset version text

4. Run `build_release.bat`

5. Confirm the EXE exists:
   - `dist\DarcsVisualPickit\DarcsVisualPickit.exe`

6. Compile `DarcsVisual_release.iss`

7. Confirm the installer exists:
   - `output\DarcsVisualPickit-Setup-v<version>.exe`

### Smoke test before publishing

1. Launch the built EXE.
2. Open a real `.nip` file.
3. Test:
   - page switching
   - search
   - performance mode on/off
   - standard mode editing
   - save
   - update center opens
4. If this release is meant to test updating, verify the updater path from the previous installed version.

### GitHub release

Upload:
- installer EXE from `output`
- app EXE from `dist\DarcsVisualPickit`

Use:
- release title from the new folder version
- body from `GITHUB_RELEASE.md`

### Stable files in this project

- `app_main.py`
- `build_release.bat`
- `DarcsVisual_release.iss`
- `GITHUB_RELEASE.md`
- `release_metadata.py`

### Main rule

For future versions, do not rename the internal files again.
Only rename the folder and update the metadata/release notes inside it.
