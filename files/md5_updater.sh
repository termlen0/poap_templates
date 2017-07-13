for f in /var/lib/tftpboot/*.py; do
    cat $f | sed '/^#md5sum/d' > $f.md5 ; sed -i \
                                              "s/^#md5sum=.*/#md5sum=\"$(md5sum $f.md5 | sed 's/ .*//')\"/" $f
done

