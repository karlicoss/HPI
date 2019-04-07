#!/usr/bin/env python3
import matplotlib.dates as md # type: ignore
import numpy as np # type: ignore
import seaborn as sns # type: ignore
import matplotlib.pyplot as plt # type: ignore

from emfit import get_datas

# def stats():
#     for jj in iter_datas():
#         # TODO fimezone??
#         # TODOgetinterval on 16 aug -- err it's pretty stupid. I shouldn't count bed exit interval...
#         st = fromts(jj['time_start'])
#         en = fromts(jj['time_end'])
#         tfmt = "%Y-%m-%d %a"
#         tot_mins = 0
#         res = []
#         res.append(f"{st.strftime(tfmt)} -- {en.strftime(tfmt)}")
#         for cls in ['rem', 'light', 'deep']:
#             mins = jj[f'sleep_class_{cls}_duration'] // 60
#             res += [cls, hhmm(mins)]
#             tot_mins += mins
#         res += ["total", hhmm(tot_mins)]
#         print(*res)


def plot_hr_trend():
    everything = get_datas()
    tss = [e.end for e in everything]
    hrs = [e.measured_hr_avg for e in everything]
    plt.figure(figsize=(15,4))
    ax = sns.pointplot(tss, hrs) # , markers=" ")
    # TODO wtf is that/??
    ax.set(ylim=(None, 70))

    plt.show()

# TODO ok, would be nice to have that every morning in timeline
# also timeline should have dynamic filters? maybe by tags
# then I could enable emfit feed and slog feed (pulled from all org notes) and see the correlation? also could pull workouts provider (and wlog) -- actually wlog processing could be moved to timeline too

plot_hr_trend()


# TODO maybe rmssd should only be computed if we have a reasonable chunk of datas

# plot_timestamped([p[0] for p in pts], [p[1] for p in pts], mavgs=[]).savefig('res.png')
# TODO X axes: show hours and only two dates
# TODO 4 is awake, 3 REM, 2 light, 1 deep

# deviartion beyond 25-75 or 75-25 is bad??
