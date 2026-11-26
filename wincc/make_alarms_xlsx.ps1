# Build TIA discrete alarm import file (KALBAR_alarms.xlsx) from plc\KB_HMI_alarms.csv,
# using the exported HMIAlarms.xlsx as template. Alarm bit %M(200+n) -> ALMW0 bit n (n<16), ALMW1 bit n-16.
param(
  [string]$Template = (Join-Path $PSScriptRoot 'HMIAlarms.xlsx'),
  [string]$Csv      = (Join-Path $PSScriptRoot '..\plc\KB_HMI_alarms.csv'),
  [string]$Tags     = (Join-Path $PSScriptRoot '..\plc\KB_HMI_tags.csv'),
  [string]$Out      = (Join-Path $PSScriptRoot 'KALBAR_alarms.xlsx')
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
function ColName([int]$i) { $s = ''; $i++; while ($i -gt 0) { $m = ($i - 1) % 26; $s = [char](65 + $m) + $s; $i = [int][math]::Floor(($i - 1) / 26) }; $s }
function Esc([string]$t) { [Security.SecurityElement]::Escape($t) }

# header row from template
$z = [IO.Compression.ZipFile]::OpenRead($Template)
function Get-Entry([string]$n) { $e = $z.GetEntry($n); $s = New-Object IO.StreamReader($e.Open()); $t = $s.ReadToEnd(); $s.Close(); $t }
[xml]$ws = Get-Entry 'xl/worksheets/sheet.xml'
$ssx = $z.GetEntry('xl/sharedStrings.xml')
$ss = @(); if ($ssx) { [xml]$sx = Get-Entry 'xl/sharedStrings.xml'; foreach ($si in $sx.sst.si) { $ss += $si.InnerText } }
$cols = foreach ($c in $ws.worksheet.sheetData.row[0].c) { if ($c.t -eq 's') { $ss[[int]$c.v] } elseif ($c.t -eq 'inlineStr') { $c.is.InnerText } else { $c.v } }
$z.Dispose()

$names = @{}; foreach ($t in (Import-Csv $Tags -Delimiter ';' -Encoding UTF8)) { if ($t.'Alamat PLC' -match '^%M(\d+)$') { $names[[int]$Matches[1]] = $t.Tag } }
$group = { param($a) if ($a -in 200) { 'Aliran sampel' } elseif ($a -in 201..205 + 214..219) { 'Instrumen' } else { 'Kualitas air' } }

$rows = Import-Csv $Csv -Delimiter ';' -Encoding UTF8
$sb = New-Object Text.StringBuilder
[void]$sb.Append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>')
function Add-Row($ri, $vals, $numeric) {
  [void]$sb.Append("<row r=`"$ri`">")
  for ($i = 0; $i -lt $cols.Count; $i++) {
    $ref = (ColName $i) + $ri; $v = [string]$vals[$cols[$i]]
    if ($numeric -contains $cols[$i] -and $v -match '^\d+$') { [void]$sb.Append("<c r=`"$ref`"><v>$v</v></c>") }
    else { [void]$sb.Append("<c r=`"$ref`" t=`"inlineStr`"><is><t xml:space=`"preserve`">$(Esc $v)</t></is></c>") }
  }
  [void]$sb.Append('</row>')
}
$hdr = @{}; foreach ($c in $cols) { $hdr[$c] = $c }
Add-Row 1 $hdr @()
$numeric = 'ID', 'Trigger bit', 'Acknowledgement bit', 'Status bit', 'Priority', 'Display suppression mask', 'PLC number', 'CPU number'
$ri = 2
foreach ($r in $rows) {
  $addr = [int]$r.Alamat; $n = $addr - 200
  $v = @{}
  foreach ($c in $cols) { $v[$c] = $(if ($c -like 'FieldInfo*') { '' } else { '<No value>' }) }
  $v['ID'] = [string]$r.No
  $v['Name'] = $(if ($names[$addr]) { 'ALM_' + ($names[$addr] -replace '^A_', '') } else { "ALM_M$addr" })
  $v[$cols[2]] = $r.'Teks alarm'
  $v['Class'] = 'Errors'
  $v['Trigger tag'] = $(if ($n -lt 16) { 'ALMW0' } else { 'ALMW1' })
  $v['Trigger bit'] = [string]($n % 16)
  $v['Trigger mode'] = 'On rising edge'
  $v['Acknowledgement bit'] = '0'; $v['Status bit'] = '0'; $v['Priority'] = '0'
  $v['Single acknowledgement'] = 'False'
  $v[($cols | ? { $_ -like 'Info text*' })] = "%M$addr - " + (& $group $addr)
  $v['Alarm annunciation'] = 'False'; $v['Display suppression mask'] = '0'; $v['PLC number'] = '0'; $v['CPU number'] = '0'
  Add-Row $ri $v $numeric; $ri++
}
[void]$sb.Append('</sheetData></worksheet>')
Copy-Item $Template $Out -Force
$z = [IO.Compression.ZipFile]::Open($Out, 'Update')
$z.GetEntry('xl/worksheets/sheet.xml').Delete()
$e = $z.CreateEntry('xl/worksheets/sheet.xml')
$w = New-Object IO.StreamWriter($e.Open(), (New-Object Text.UTF8Encoding $false)); $w.Write($sb.ToString()); $w.Close()
$z.Dispose()
"Wrote $Out with $($ri - 2) alarms"
