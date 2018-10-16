from emfit import get_datas

for e in get_datas():
    # print("-------")
    print(f"{e.end} {e.measured_hr_avg} {e.summary}")


# TODO get average HR
# TODO get 'quality', that is amount of time it actually had signal

from kython.plotting import plot_timestamped
everything = get_datas()
tss = [e.end for e in everything]
hrs = [e.measured_hr_avg for e in everything]

plot_timestamped(
    tss,
    hrs,
    ratio=(15, 3),
    mavgs=[(5, 'blue'), (10, 'green')],
    marker='.',
    ylimits=[40, 70],
   ).savefig('hrs.png')
