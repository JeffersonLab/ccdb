#!/usr/bin/env perl
$groupid = 267;
open (YPCAT,"ypcat group |");
while (<YPCAT>) {
    if (/:$groupid:/) {
	chomp;
	@t = split/:$groupid:/;
	print $t[1];
    }
}
print "\n";
exit;
