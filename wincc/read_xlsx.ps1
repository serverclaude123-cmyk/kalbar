param([string]$Path, [int]$MaxRows = 10)
# Dump an xlsx (sheet names + first rows) without Excel
Add-Type -AssemblyName System.IO.Compression.FileSystem
$z = [IO.Compression.ZipFile]::OpenRead($Path)
function Get-Entry([string]$n) { $e = $z.GetEntry($n); if ($e) { $s = New-Object IO.StreamReader($e.Open()); $t = $s.ReadToEnd(); $s.Close(); $t } }
[xml]$wb = Get-Entry 'xl/workbook.xml'
[xml]$rels = Get-Entry 'xl/_rels/workbook.xml.rels'
$ss = @()
$ssx = Get-Entry 'xl/sharedStrings.xml'
if ($ssx) { [xml]$sx = $ssx; foreach ($si in $sx.sst.si) { $ss += $si.InnerText } }
foreach ($sh in $wb.workbook.sheets.sheet) {
  $rid = $sh.GetAttribute('id', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
  $target = ($rels.Relationships.Relationship | ? Id -eq $rid).Target
  $p = 'xl/' + ($target -replace '^/xl/', '')
  "== SHEET '$($sh.name)' -> $p"
  [xml]$ws = Get-Entry $p
  $n = 0
  foreach ($row in $ws.worksheet.sheetData.row) {
    $n++; if ($n -gt $MaxRows) { break }
    $vals = foreach ($c in $row.c) {
      $v = $c.v; if ($c.t -eq 's') { $v = $ss[[int]$v] } elseif ($c.t -eq 'inlineStr') { $v = $c.is.InnerText }
      "$($c.r)=$v"
    }
    "  " + ($vals -join ' | ')
  }
}
$z.Dispose()

