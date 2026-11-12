[Console]::OutputEncoding=[Text.Encoding]::UTF8
$out = 'D:\Tools\walkman-inventory.jsonl'
$files = Get-ChildItem -LiteralPath 'D:\WALKMAN' -Recurse -File | Where-Object { '.mp3','.m4a','.flac','.wav','.oma' -contains $_.Extension.ToLower() }
$rows = New-Object System.Collections.Generic.List[string]
$n = 0
foreach ($f in $files) {
  $rel = $f.FullName.Substring(10)
  $parts = $rel -split '\\'
  $top = $parts[0]
  $title=''; $artist=''; $album=''; $genre=''
  try {
    $j = & ffprobe -v quiet -print_format json -show_entries 'format_tags=title,artist,album,album_artist,genre' -- "$($f.FullName)" 2>$null | ConvertFrom-Json
    if ($j.format.tags) {
      $title = [string]$j.format.tags.title
      $artist = [string]$j.format.tags.artist
      if (-not $artist) { $artist = [string]$j.format.tags.album_artist }
      $album = [string]$j.format.tags.album
      $genre = [string]$j.format.tags.genre
    }
  } catch {}
  $row = @{ path=$rel; top=$top; tagTitle=$title; tagArtist=$artist; tagAlbum=$album; tagGenre=$genre } | ConvertTo-Json -Compress
  $rows.Add($row)
  $n++
  if ($n % 400 -eq 0) { Write-Host "progress $n" }
}
[IO.File]::WriteAllLines($out, $rows, (New-Object Text.UTF8Encoding($false)))
Write-Host ('DONE ' + $rows.Count)
