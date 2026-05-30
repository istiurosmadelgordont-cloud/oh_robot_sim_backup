
$branch = "master_chunked"
git checkout --orphan $branch
git rm -rf .
$files = Get-ChildItem -File -Recurse | Where-Object { $_.FullName -notmatch "\\\.git\\" -and $_.FullName -notmatch "chunk_push.ps1" }
$batchSize = 40MB
$currentSize = 0
$batchCount = 1

foreach ($file in $files) {
    git add $file.FullName
    $currentSize += $file.Length
    
    if ($currentSize -ge $batchSize) {
        git commit -m "chore: upload chunk $batchCount"
        git push -u origin $branch`:master
        $currentSize = 0
        $batchCount++
    }
}

if ($currentSize -gt 0) {
    git commit -m "chore: upload final chunk"
    git push -u origin $branch`:master
}

