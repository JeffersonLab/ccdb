#pragma once
#include "DDataProvider.h"
#ifndef WIN32
#include <dirent.h>
#include <stdio.h>
#endif
namespace ccdb
{
#ifndef WIN32
	int listdir(const char *path) 
	{
		struct dirent *entry;
		DIR *dp;

		dp = opendir(path);
		if (dp == NULL) {
			perror("opendir");
			return -1;
		}

		while((entry = readdir(dp)))
			puts(entry->d_name);

		closedir(dp);
		return 0;
	}
#endif

class DFileDataProvider : public DDataProvider
{
public:
	DFileDataProvider(void);
	~DFileDataProvider(void);
	virtual bool Connect(std::string connectionString);

	virtual void Disconnect();
};
}
