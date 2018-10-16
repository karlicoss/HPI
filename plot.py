#!/usr/bin/env python3
import matplotlib.dates as md # type: ignore
import numpy as np # type: ignore
import seaborn as sns # type: ignore
import matplotlib.pyplot as plt

from emfit import get_datas


def plot_file(jj: str):
    pts = jj['sleep_epoch_datapoints']


    tss = [datetime.fromtimestamp(p[0]) for p in pts]
    vals = [p[1] for p in pts]

    plt.figure(figsize=(20,10))
    plt.plot(tss, vals)


    xformatter = md.DateFormatter('%H:%M')
    xlocator = md.MinuteLocator(interval = 15)

    ## Set xtick labels to appear every 15 minutes
    plt.gcf().axes[0].xaxis.set_major_locator(xlocator)

    ## Format xtick labels as HH:MM
    plt.gcf().axes[0].xaxis.set_major_formatter(xformatter)



    plt.xlabel('time')
    plt.ylabel('phase')
    plt.title('Sleep phases')
    plt.grid(True)
    plt.savefig(f"{f}.png")
    plt.close() # TODO
    # plt.show()

    pass


def plot_all():
    for jj in iter_datas():
        plot_file(jj)


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


def stats():
    datas = get_datas()
    cur = datas[0].date
    for jj in datas:
        # import ipdb; ipdb.set_trace() 
        while cur < jj.date:
            cur += timedelta(days=1)
            if cur.weekday() == 0:
                print("---")
            if cur != jj.date:
                print(" ")
        # cur = jj.date
        print(f"{jj.date.strftime('%m.%d %a')} {jj.hrv_morning:.0f} {jj.hrv_evening:.0f} {jj.hrv_morning - jj.hrv_evening:3.0f} {hhmm(jj.sleep_minutes)} {jj.hrv_lf}/{jj.hrv_hf} {jj.sleep_hr_coverage:3.0f}")


def plot_recovery_vs_hr_percentage():
    sns.set(color_codes=True)
    xs = []
    ys = []
    for jj in get_datas():
        xs.append(jj.hrv_morning - jj.hrv_evening)
        ys.append(jj.sleep_hr_coverage)
    ax = sns.regplot(x=xs, y=ys) # "recovery", y="percentage", data=pdata)
    ax.set(xlabel='recovery', ylabel='percentage')
    plt.show()


# TODO ah. it's only last segment?
def plot_hr():
    jj = get_datas()[-1]
    tss, uu = jj.sleep_hr
    tss = tss[::10]
    uu = uu[::10]
    plt.figure(figsize=(15,4))
    ax = sns.pointplot(tss, uu, markers=" ")
    # TODO wtf is that/??
    ax.set(ylim=(None, 200))

    plt.show()

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

# TODO could plot 'recovery' thing and see if it is impacted by workouts


# TODO time_start, time_end

# plot_hrv()
# stats()
# plot_recovery_vs_hr_percentage()
# stats()
plot_hr_trend()
# import matplotlib
# matplotlib.use('Agg')


# TODO maybe rmssd should only be computed if we have a reasonable chunk of datas
# also, trust it only if it's stable

# plot_timestamped([p[0] for p in pts], [p[1] for p in pts], mavgs=[]).savefig('res.png')
# TODO X axes: show hours and only two dates
# TODO 4 is awake, 3 REM, 2 light, 1 deep




# deviartion beyond 25-75 or 75-25 is bad??
