import matplotlib.pyplot as plt
import map_interactive as mi
import ml


def map_tester():
	'tester program to run the build basemap and return the fig'
	profile = ml.read_prof_file(ml.profile_filename)
	pro = profile[0]
	print(f'{pro}')
	fig = plt.figure()
	m = mi.build_basemap(fig=fig,profile=pro)
	line = ml.init_plot(m,start_lat=pro['Start_lat'],start_lon=pro['Start_lon'],color='red')
	line.labels_points = mi.plot_map_labels(m,'labels.txt',alpha=0.4)
	fig.show()
	
	return fig, m, line