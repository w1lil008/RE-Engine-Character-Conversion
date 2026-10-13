param(
    [ValidateSet('Extract','Analyze','Prepare','Build','Preview','Align','Validate','Test','AllOffline')]
    [string]$Step = 'Validate',
    [string]$Python = (Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$portableBlender = Join-Path $projectRoot 'tools/blender-4.3.2-windows-x64/blender.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Supply -Python with a Python 3.12 executable containing numpy and Pillow.' }
if (-not (Test-Path -LiteralPath $portableBlender -PathType Leaf)) { throw 'Pinned portable Blender 4.3.2 is missing. See config/toolchain.lock.json.' }
function Invoke-PythonStep([string]$Log, [string[]]$Arguments) {
    & $Python @Arguments *> (Join-Path $projectRoot "reports/$Log.log")
    if ($LASTEXITCODE -ne 0) { throw "$Log failed. Read reports/$Log.log" }
    Write-Output "$Log completed."
}
function Invoke-BlenderStep([string]$Log, [string]$Script) {
    & $portableBlender -b --factory-startup --python-exit-code 1 --python "scripts/$Script" *> (Join-Path $projectRoot "reports/$Log.log")
    if ($LASTEXITCODE -ne 0) { throw "$Log failed. Read reports/$Log.log" }
    Write-Output "$Log completed; game functionality remains unverified."
}
function Invoke-Stage([string]$Stage) {
    switch ($Stage) {
        'Extract' {
            Invoke-PythonStep 're8_extraction' @('scripts/extract_assets.py','re8','--paths','config/re8_dependencies.txt')
            Invoke-PythonStep 'clothing_extraction' @('scripts/extract_assets.py','re8','--extensions','disabled','--paths','config/re8_clothing.txt','--report-name','re8_clothing')
            Invoke-PythonStep 're9_extraction' @('scripts/extract_assets.py','re9','--extensions','mesh,mdf2,fbxskel,chain2,clsp,jntexprgraph,jcns,pfb')
        }
        'Analyze' {
            Invoke-PythonStep 'analysis' @('scripts/analyze_assets.py')
            Invoke-PythonStep 'dependencies' @('scripts/collect_dependencies.py')
            Invoke-PythonStep 're8_extraction' @('scripts/extract_assets.py','re8','--paths','config/re8_dependencies.txt')
        }
        'Prepare' {
            Invoke-BlenderStep 'clothing_weights' 'prepare_clothing_weights.py'
            Invoke-PythonStep 'clothing_regularization' @('scripts/regularize_clothing_weights.py')
        }
        'Build' {
            Invoke-PythonStep 'mesh_build' @('scripts/build_meshes.py')
            Invoke-PythonStep 'material_build' @('scripts/build_materials.py')
            Invoke-PythonStep 're9_material_dependencies' @('scripts/extract_assets.py','re9','--extensions','disabled','--paths','config/re9_material_dependencies.txt','--report-name','re9_material_dependency')
            Invoke-PythonStep 'baseline_previews' @('scripts/prepare_baseline_previews.py')
        }
        'Preview' { Invoke-BlenderStep 'blender' 'blender_scene.py' }
        'Align' {
            Invoke-PythonStep 'source_seam_audit' @('scripts/audit_source_seams.py')
            Invoke-BlenderStep 'alignment' 'blender_alignment.py'
            Invoke-BlenderStep 'assembled_seam_audit' 'audit_assembled_seams.py'
            Invoke-BlenderStep 'garment_seam_audit' 'audit_garment_seams.py'
        }
        'Validate' { Invoke-PythonStep 'validation' @('scripts/validate_mod.py') }
        'Test' { Invoke-PythonStep 'tests' @('-m','unittest','discover','-s','tests','-v') }
    }
}
Push-Location $projectRoot
try {
    if ($Step -eq 'AllOffline') {
        foreach ($stage in @('Extract','Analyze','Prepare','Build','Preview','Align','Validate','Test')) { Invoke-Stage $stage }
    } else { Invoke-Stage $Step }
} finally { Pop-Location }
Write-Output 'Offline stage completed. Packaging and game installation are separate operations; gameplay remains unverified.'

