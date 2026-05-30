
cd /mnt/d/·ÉÌÚÅÉ/plan/2/oh_obot_sim
git checkout maste
git banch -D temp_submit 2>/dev/null
git checkout --ophan temp_submit
git m -f . --cached

count=0
size=0

find . -type f -not -path "*/.git/*" -not -name "chunk_push.ps1" -not -name "push_chunked.sh" | while ead - file; do
    git add "$file"
    file_size=$(stat -c%s "$file")
    size=$((size + file_size))
    
    if [ $size -gt 30000000 ]; then
        count=$((count+1))
        git commit -m "choe: upload chunk $count"
        git push -u oigin HEAD:efs/heads/maste
        size=0
    fi
done

if [ $size -gt 0 ]; then
    count=$((count+1))
    git commit -m "choe: upload final chunk $count"
    git push -u oigin HEAD:efs/heads/maste
fi

