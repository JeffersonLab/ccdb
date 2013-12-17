#ifndef TimeProvider_h__
#define TimeProvider_h__

#include <time.h>

namespace ccdb
{
	namespace ClockSources
	{
		typedef enum {
			Realtime,
			Monotonic,
			RealtimeHr,
			MonotonicHr
		} Sources;
	}
	typedef ClockSources::Sources ClockSourcesEnum;

	
	class TimeProvider
	{
	public:

        /** @brief returns unix time since epoch 
         * 
         * @remark if @see TimeUnitTest is set to true, returns the value set by @see SetUnitTestTime
         * @return returns unix time since epoch 
         */
		static time_t GetUnixTimeStamp(ClockSourcesEnum source);


        /** @brief makes function @see GetUnixTimeStamp to return value set by SetUnitTestTime
         */
        static void SetTimeUnitTest(bool value) {mIsTimeUnitTest = value;}


        /** @brief Get flag that function @see GetUnixTimeStamp to return value set by SetUnitTestTime
         */
        static time_t GetTimeUnitTest() { return mIsTimeUnitTest;}


        /** @brief sets value for unit testing. Works after TimeUnitTest(true) is set;
        */
        static void SetUnitTestTime(time_t time){ mUnitTestTime = time;}


        /** @brief Delay in ms
         */
        static void Delay(time_t ms);

    private:
        static time_t mUnitTestTime; ///@see TimeUnitTest and SetUnitTestTime
        static bool mIsTimeUnitTest; ///@see TimeUnitTest and SetUnitTestTime
	};
}


#endif // TimeProvider_h__