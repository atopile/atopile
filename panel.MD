# panel.kicad_pcb Benchmark

Command:
`/tmp/panel_bench_now --input-file panel.kicad_pcb --warmup 0 --samples 1`

Input bytes (latest run): `122,020,605`

| Stage     | Baseline ms | Latest ms | Speedup | Baseline peak+ KiB | Latest peak+ KiB | Mem delta |
|-----------|------------:|----------:|--------:|-------------------:|-----------------:|----------:|
| tokenizer | 988.862     | 413.539   | 2.39x   | 1,149,079.980      | 344,724.100      | -70.0%    |
| ast       | 1700.233    | 751.858   | 2.26x   | 1,688,048.643      | 748,175.508      | -55.7%    |
| parser    | 75325.976   | 356.749   | 211.13x | 168,473.025        | 168,473.064      | +0.0%     |
| encode    | 2232.663    | 309.460   | 7.21x   | 1,162,067.412      | 0.000            | -100.0%   |
| pretty    | 557.183     | 319.791   | 1.74x   | 242,651.151        | 242,651.151      | +0.0%     |
