# TODO this should be integrated into dashboard
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


# then I could enable emfit feed and slog feed (pulled from all org notes) and see the correlation? also could pull workouts provider (and wlog) -- actually wlog processing could be moved to timeline too

# TODO maybe rmssd should only be computed if we have a reasonable chunk of datas

# TODO X axes: show hours and only two dates
# TODO 4 is awake, 3 REM, 2 light, 1 deep

# deviartion beyond 25-75 or 75-25 is bad??
