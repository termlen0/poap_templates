for f in /home/ajay/Projects/misc/list_of_dicts/*.py; do
    cat $f | sed '/^#md5sum/d' > $f.md5 ; sed -i \
                                              "s/^#md5sum=.*/#md5sum=\"$(md5sum $f.md5 | sed 's/ .*//')\"/" $f
    echo $f
done

