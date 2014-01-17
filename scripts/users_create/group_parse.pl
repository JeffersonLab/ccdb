#!/usr/bin/env perl
$groupid = 267;
open (YPCAT,"ypcat group |");
$group_count = 0;
while (<YPCAT>) {
    if (/:$groupid:/) {
	$group_count++;
	if ($group_count > 1) {print ',';}
	chomp;
	@t = split/:$groupid:/;
	print $t[1];
    }
}
print "\n";
exit;
