#!/bin/bash
host=localhost
scratch_dir=./ccdb_convert_scratch
echo CCDB_HOME is $CCDB_HOME
echo host is $host
echo scratch_dir is $scratch_dir
read -p "press enter to continue..." dummy
echo delete scratch_dir
rm -rf $scratch_dir
echo create scratch_dir
mkdir -p $scratch_dir
echo dump ccdb 1
mysqldump -h$host -uccdb_user ccdb > $scratch_dir/ccdb1.sql
echo drop ccdb 2 database
mysql -h$host -uccdb_user -e "drop database if exists ccdb2"
echo create ccdb 2 database
mysql -h$host -uccdb_user -e "create database ccdb2"
echo load ccdb 2 database from ccdb 1 dump
mysql -h$host -uccdb_user ccdb2 < $scratch_dir/ccdb1.sql
echo convert ccdb 2 to ccdb 2 schema
mysql -h$host -uccdb_user ccdb2 < $CCDB_HOME/sql/update_1.00_2.00.sqlite.sql
