# Build TIA HMI tag import file (KALBAR_tags.xlsx) from plc\KB_HMI_tags.csv,
# using the exported HMITags_sample.xlsx as template (same columns/styles).
param(
  [string]$Template = (Join-Path $PSScriptRoot 'HMITags_sample.xlsx'),
  [string]$Csv      = (Join-Path $PSScriptRoot '..\plc\KB_HMI_tags.csv'),
  [string]$Out      = (Join-Path $PSScriptRoot 'KALBAR_tags.xlsx'),
  [string]$Table    = 'KALBAR',
  [string]$Conn     = 'Connection_1',
  [switch]$NoScaling
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem

$cols = 'Name','Path','Connection','PLC tag','DataType','HMI DataType','Length','Coding','Access Method','Address','Start value','Quality Code','Persistency','Substitute value','Tag value [en-US]','Update Mode','Comment [en-US]','Limit Upper 2 Type','Limit Upper 2','Limit Lower 2 Type','Limit Lower 2','Linear scaling','End value PLC','Start value PLC','End value HMI','Start value HMI','Synchronization','OPC Read Protection','OPC Write Protection','REST Read Access','REST Write Access'

function ColName([int]$i) { $s = ''; $i++; while ($i -gt 0) { $m = ($i - 1) % 26; $s = [char](65 + $m) + $s; $i = [int][math]::Floor(($i - 1) / 26) }; $s }
function Esc([string]$t) { [Security.SecurityElement]::Escape($t) }

$rows = Import-Csv $Csv -Delimiter ';' -Encoding UTF8
$data = New-Object System.Collections.Generic.List[object]
foreach ($r in $rows) {
  $addr = $r.'Alamat PLC'
  $isBit = $addr -match '^%M\d+$'
  $unit = $r.Satuan
  $scaled = (-not $NoScaling) -and (-not $isBit) -and ($unit -like 'x0,01*')
  $comment = $r.Keterangan
  if ($unit) { $comment = "[$unit] $comment" }
  $v = [ordered]@{}
  foreach ($c in $cols) { $v[$c] = '<No Value>' }
  $v['Name'] = $r.Tag; $v['Path'] = $Table; $v['Connection'] = $Conn
  if ($isBit) { $v['DataType'] = 'Bit'; $v['HMI DataType'] = 'Bool'; $v['Length'] = '1' }
  else { $v['DataType'] = 'Int'; $v['HMI DataType'] = $(if ($scaled) { 'Real' } else { 'Int' }); $v['Length'] = '2' }
  $v['Coding'] = 'Binary'; $v['Access Method'] = 'Absolute access'; $v['Address'] = $addr
  $v['Quality Code'] = 'False'; $v['Persistency'] = 'False'; $v['Update Mode'] = 'Client/Server wide'
  $v['Comment [en-US]'] = $comment
  $v['Limit Upper 2 Type'] = 'None'; $v['Limit Lower 2 Type'] = 'None'
  if ($scaled) { $v['Linear scaling'] = 'True'; $v['End value PLC'] = '10000'; $v['Start value PLC'] = '0'; $v['End value HMI'] = '100'; $v['Start value HMI'] = '0' }
  else { $v['Linear scaling'] = 'False'; $v['End value PLC'] = '10'; $v['Start value PLC'] = '0'; $v['End value HMI'] = '100'; $v['Start value HMI'] = '0' }
  $v['Synchronization'] = 'False'; $v['OPC Read Protection'] = 'False'; $v['OPC Write Protection'] = 'False'
  $data.Add($v)
}

# sheet XML with inline strings (numbers as numbers)
$numCols = 'Length','End value PLC','Start value PLC','End value HMI','Start value HMI'
$sb = New-Object Text.StringBuilder
[void]$sb.Append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheetData>')
function Add-Row($rowIdx, $values, $isHeader) {
  [void]$sb.Append("<row r=`"$rowIdx`">")
  for ($i = 0; $i -lt $cols.Count; $i++) {
    $ref = (ColName $i) + $rowIdx
    $val = [string]$values[$i]
    if (-not $isHeader -and ($numCols -contains $cols[$i]) -and $val -match '^-?\d+(\.\d+)?$') { [void]$sb.Append("<c r=`"$ref`"><v>$val</v></c>") }
    else { [void]$sb.Append("<c r=`"$ref`" t=`"inlineStr`"><is><t xml:space=`"preserve`">$(Esc $val)</t></is></c>") }
  }
  [void]$sb.Append('</row>')
}
Add-Row 1 $cols $true
$ri = 2
foreach ($v in $data) { Add-Row $ri @($v.Values) $false; $ri++ }
[void]$sb.Append('</sheetData></worksheet>')

Copy-Item $Template $Out -Force
$z = [IO.Compression.ZipFile]::Open($Out, 'Update')
$z.GetEntry('xl/worksheets/sheet.xml').Delete()
$e = $z.CreateEntry('xl/worksheets/sheet.xml')
$w = New-Object IO.StreamWriter($e.Open(), (New-Object Text.UTF8Encoding $false)); $w.Write($sb.ToString()); $w.Close()
$z.Dispose()
"Wrote $Out with $($data.Count) tags ($(@($data | ? { $_['Linear scaling'] -eq 'True' }).Count) scaled)"
