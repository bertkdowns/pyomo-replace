# Metrics
| case | model | duration_s | input_tokens | output_tokens | reasoning_tokens | cache_read_tokens | cache_write_tokens | patches | lines_added | lines_removed | model_runs | model_run_failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geothermal/base_case | gpt-5.6-terra | 348.859 | 143399 | 4125 | 5752 | 1823232 |  | 2 | 41 | 8 | 5 | 4 |
| geothermal/base_with_guesses | gpt-5.6-terra | 385.333 | 102538 | 5696 | 5968 | 2017792 |  | 8 | 82 | 25 | 10 | 7 |
| geothermal/replaced_case | gpt-5.6-terra | 110.529 | 68774 | 2547 | 1553 | 522752 |  | 1 | 52 | 6 | 2 | 1 |
| heat-integration/base_case | gpt-5.6-terra | 378.836 | 161238 | 6051 | 4266 | 1996800 |  | 8 | 52 | 28 | 9 | 6 |
| heat-integration/base_with_guesses | gpt-5.6-terra | 426.478 | 150738 | 7888 | 5959 | 1411584 |  | 10 | 132 | 53 | 12 | 11 |
| heat-integration/replaced_case | gpt-5.6-terra | 207.406 | 58580 | 3338 | 2284 | 700928 |  | 2 | 59 | 6 | 3 | 2 |
| milk-evaporator/base_case | gpt-5.6-terra | 109.605 | 51083 | 2447 | 704 | 409600 |  | 1 | 29 | 3 | 3 | 2 |
| milk-evaporator/base_with_guesses | gpt-5.6-terra | 93.516 | 62338 | 1792 | 521 | 262144 |  | 1 | 26 |  | 3 | 2 |
| milk-evaporator/replaced_case | gpt-5.6-terra | 113.809 | 51143 | 2380 | 843 | 500736 |  | 1 | 30 | 2 | 2 | 1 |
