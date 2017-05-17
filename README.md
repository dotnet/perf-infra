# Supported platform matrix



| Platform        | ISA           | Status  | Notes |
| ------------- |:-------------:|:-----:|:-----|
| Windows      | x64 | :white_check_mark: | n/a |
| Windows      | x86      |   :large_orange_diamond: | ready to try: need Windows x86 machines in the lab |
| Windows      | ARM64      |   :red_circle: | not planned |
| Windows      | ARM32      |   :red_circle: | not planned |
| Linux (Ubuntu 16.04) | x64      |    :large_orange_diamond: | ready to try: needs dedicated Linux x64 machines in the lab |
| Linux (Ubuntu 16.04) | x86      |    :red_circle: | not supported |


# Supported measurements matrix



| Measurement                          | Description  | Mehodology |
| ------------------------------------ |:-------------| :----------|
| _Server startup time_                | Time for server application to start and be ready to serve incoming requests | Measure average elapsed time from beginning of `Main` to completion of `IWebHost.Start( )`. Average across 100 independent iterations. |
| _Time to first request_              | Time for serving first incoming request | Measure elapsed time from `IWebHost.Start( )` completion to completion of first request at the client site as `client.GetAsync("http://localhost:5000").Result` completes. |
| _Steady state average RPS_           | Average RPS (Requests-Per-Second) at steady state | Issue a warm-up request, then measure average time for a request across 100 consecutive request. Average across 100 independent iterations. No data is discarded. |
| _Steady state shortest request time_ | Shortest time to serve a request | Same as _Steady state average RPS_, but records shortest time only |
| _Steady state longest request time_  | Longest time to serve a request | Same as _Steady state average RPS_, but records longest time only |

