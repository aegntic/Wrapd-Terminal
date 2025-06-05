@echo off
:: WRAPD Windows Build Script

echo 🪟 WRAPD Windows Build Script
echo ===============================

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is required but not installed
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python found

:: Get script directory
set SCRIPT_DIR=%~dp0
set BUILD_DIR=%SCRIPT_DIR%build
set DIST_DIR=%SCRIPT_DIR%dist

echo 📂 Setting up build environment...

:: Create build directories
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

:: Check for uv
uv --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  uv not found, installing...
    powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    :: Add uv to PATH for current session
    set PATH=%USERPROFILE%\.cargo\bin;%PATH%
)

echo ✅ uv found

:: Create virtual environment
echo 🐍 Creating virtual environment...
cd /d "%SCRIPT_DIR%"
uv venv --python 3.8
call .venv\Scripts\activate.bat

:: Install dependencies
echo 📦 Installing dependencies...
uv pip install -r requirements.txt
uv pip install pyinstaller
uv pip install auto-py-to-exe

:: Check PyQt5
echo 🖥️  Checking PyQt5...
python -c "import PyQt5; print('PyQt5 OK')"
if errorlevel 1 (
    echo ❌ PyQt5 installation failed
    pause
    exit /b 1
)

:: Build with PyInstaller
echo 🔨 Building WRAPD.exe...

:: Create PyInstaller spec file
echo Creating PyInstaller spec file...
python -c "
import PyInstaller.__main__
PyInstaller.__main__.run([
    'src/main.py',
    '--name=WRAPD',
    '--windowed',
    '--onedir',
    '--distpath=dist',
    '--workpath=build',
    '--add-data=resources;resources',
    '--icon=resources/icons/wrapd.ico',
    '--hidden-import=PyQt5',
    '--hidden-import=PyQt5.QtCore',
    '--hidden-import=PyQt5.QtGui',
    '--hidden-import=PyQt5.QtWidgets',
    '--hidden-import=aiohttp',
    '--hidden-import=keyring',
    '--hidden-import=prompt_toolkit',
    '--hidden-import=pygments',
    '--hidden-import=paramiko',
    '--noconsole'
])
"

if not exist "%DIST_DIR%\WRAPD\WRAPD.exe" (
    echo ❌ Build failed - executable not found
    pause
    exit /b 1
)

echo ✅ WRAPD.exe created successfully

:: Create installer with NSIS (if available)
echo 💾 Creating Windows installer...

:: Check for NSIS
makensis /VERSION >nul 2>&1
if errorlevel 1 (
    echo ⚠️  NSIS not found, skipping installer creation
    echo Download NSIS from https://nsis.sourceforge.io/
    goto :skip_installer
)

:: Create NSIS script
echo Creating NSIS installer script...
(
echo !define APPNAME "WRAPD"
echo !define COMPANYNAME "aegntic.ai"
echo !define DESCRIPTION "Warp Replacement with AI-Powered Delivery"
echo !define VERSIONMAJOR 1
echo !define VERSIONMINOR 0
echo !define VERSIONBUILD 0
echo !define HELPURL "https://github.com/aegntic/wrapd"
echo !define UPDATEURL "https://github.com/aegntic/wrapd/releases"
echo !define ABOUTURL "https://aegntic.ai"
echo !define INSTALLSIZE 150000
echo.
echo RequestExecutionLevel admin
echo InstallDir "$PROGRAMFILES\${APPNAME}"
echo.
echo Name "${APPNAME}"
echo Icon "resources\icons\wrapd.ico"
echo outFile "dist\WRAPD-1.0.0-Windows-Setup.exe"
echo.
echo page directory
echo page instfiles
echo.
echo section "install"
echo 	setOutPath $INSTDIR
echo 	file /r "dist\WRAPD\*"
echo 	
echo 	writeUninstaller "$INSTDIR\uninstall.exe"
echo 	
echo 	createDirectory "$SMPROGRAMS\${APPNAME}"
echo 	createShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\WRAPD.exe"
echo 	createShortCut "$SMPROGRAMS\${APPNAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe"
echo 	createShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\WRAPD.exe"
echo 	
echo 	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
echo 	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$INSTDIR\uninstall.exe"
echo 	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "InstallLocation" "$INSTDIR"
echo 	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayIcon" "$INSTDIR\WRAPD.exe"
echo 	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "${COMPANYNAME}"
echo 	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "HelpLink" "${HELPURL}"
echo 	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "URLUpdateInfo" "${UPDATEURL}"
echo 	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "URLInfoAbout" "${ABOUTURL}"
echo 	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}"
echo 	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMajor" ${VERSIONMAJOR}
echo 	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMinor" ${VERSIONMINOR}
echo 	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoModify" 1
echo 	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoRepair" 1
echo 	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "EstimatedSize" ${INSTALLSIZE}
echo sectionEnd
echo.
echo section "uninstall"
echo 	delete "$INSTDIR\*.*"
echo 	rmDir /r "$INSTDIR"
echo 	delete "$SMPROGRAMS\${APPNAME}\*.*"
echo 	rmDir "$SMPROGRAMS\${APPNAME}"
echo 	delete "$DESKTOP\${APPNAME}.lnk"
echo 	DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
echo sectionEnd
) > installer.nsi

makensis installer.nsi

if exist "dist\WRAPD-1.0.0-Windows-Setup.exe" (
    echo ✅ Windows installer created successfully
    del installer.nsi
) else (
    echo ⚠️  Installer creation failed
)

:skip_installer

echo ✅ Windows build complete!
echo 📱 Executable: %DIST_DIR%\WRAPD\WRAPD.exe
if exist "dist\WRAPD-1.0.0-Windows-Setup.exe" (
    echo 💾 Installer: dist\WRAPD-1.0.0-Windows-Setup.exe
)

echo.
echo 🎉 Build completed successfully!
echo To run: Double-click WRAPD.exe in the dist\WRAPD folder
echo To install: Run the installer if created

pause