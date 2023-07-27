wget https://iabp.apl.uw.edu/TABLES/ArcticTable_Current.txt
awk --field-separator ';' {'print $4","$9","$8",sk"'} ArcticTable_Current.txt >> labels.txt
