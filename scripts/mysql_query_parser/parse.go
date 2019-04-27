package main

import (
	"bufio"
	"fmt"
	"log"
	"os"
	"regexp"
	"strings"
)

func main() {
	file, err := os.Open("/home/romanov/halld/ccdb/hallddb-mariadb-slow-queries-20190423.log")
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()


	runMinRegexp := regexp.MustCompile(`runMin <= (?P<runMin>\d+)`)
	variationRegexp := regexp.MustCompile(`assignments.variationId= (?P<varId>\d+)`)
	//fmt.Printf("%#v\n", r.FindStringSubmatch(`2015-05-27`))
	//fmt.Printf("%#v\n", r.SubexpNames())
	
	lineNum := 0
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		//line = strings.Replace(line, "'", "", -1)
		line := scanner.Text()

		if strings.HasPrefix(line, "SELECT `assignments`.`id` AS `asId`, `constantSets`.`vault`") {
			line = strings.Replace(line, "`", "", -1)
			line = strings.Replace(line, "'", "", -1)

			fmt.Println(line)
			fmt.Printf("%#v\n", runMinRegexp.FindStringSubmatch(line))
			fmt.Printf("%#v\n", variationRegexp.FindStringSubmatch(line))

		}


		lineNum++
		if lineNum > 1000 {
			break
		}
	}

	if err := scanner.Err(); err != nil {
		log.Fatal(err)
	}
}