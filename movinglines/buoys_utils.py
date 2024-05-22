def __init__():
    """
    Name:  

        buoys_utils

    Purpose:  

        Module regrouping codes that are used to load buoy information for ARCSIX
        See each function within this module

    Dependencies:

        - numpy
        - datetime
		- requests

    Needed Files:

      None

    Modification History:

        Written: Samuel LeBlanc, Santa Cruz, CA, 2024-05-08
				- based on information availabel from: https://www.cryosphereinnovation.com/docs/visualizing-simb3-data-using-python
    """
    pass
    
def load_SIMB3_buoys(last_only=True,field_list = ['latitude','longitude','time_stamp','incident','air_temp','reflected'],convert_time_stamp=True,verbose=True,print_list=True,marker_str='vb'):
    """
    function to request most recent buoy data for SIMB3:
        https://www.cryosphereinnovation.com/data/
        returns dict with list of data for the last points only (unless last_only=False)
    """
    import requests
    import numpy as np
    
    API_key = '3vzzTCrhgJq21JmxpCQvm41jcvgh4yt7'
    base_url = 'https://api.cryosphereinnovation.com/public/deployment/data/{buoy_dep_id}/?{extra_fields}'
    Buoy_list = [('SIMB3J','416791b6-2e94-430d-9abf-243ee61928fd'),
                  ('SIMB3K','ad35b741-8057-447f-aeec-9bf77758bbbe'),
                  ('SIMB3L','60f4bc71-6942-49dc-89ab-d5434424e6dc'),
                  ('SIMB3M','b0b375b6-1b79-4ec2-a782-44e13216ec49'),
                  ('SIMB3N','08e8df7f-cc43-4360-8390-ac2a5afd55df'),
                  ('SIMB3O','2986a270-4686-4a6c-b608-c28d96bb8e40'),
                  ('SIMB3P','a2af67ec-ce23-47e0-98e5-9610248cb605'),
                  ('SIMB3Q','b3251af2-037b-4651-a433-ff50e6e30288'),
                  ('SIMB3R','0ffc82c0-91b4-47fb-a62d-8b16b583196b')]
    extra_fields = 'field='+'&field='.join(c for c in field_list)
    
    out_data = {}
    for b in Buoy_list:
        if verbose:print('Getting Buoy: {}'.format(b[0]))
        response = requests.get(base_url.format(buoy_dep_id=b[1],extra_fields=extra_fields), headers={'Authorization':'Bearer {api_key}'.format(api_key=API_key)}).json()
        out_data[b[0]] = {}
        for key in response[0]:
            out_data[b[0]][key] = np.array([r[key] for r in response])
        if convert_time_stamp and 'time_stamp' in response[0]:
            out_data[b[0]]['time_stamp'] = np.asarray(out_data[b[0]]['time_stamp']-25568-1, dtype='datetime64[s]')
        if last_only:
            for key in out_data[b[0]]:
                out_data[b[0]][key] = out_data[b[0]][key][-1]
        
    if print_list:
        for b in out_data:
            try:
                if last_only:
                    print('{name}, {lon},{lat},{marker}'.format(name=b,lon=out_data[b]['longitude'],lat=out_data[b]['latitude'],marker=marker_str))
                else:
                    print('{name}, {lon},{lat},{marker}'.format(name=b,lon=out_data[b]['longitude'][-1],lat=out_data[b]['latitude'][-1],marker=marker_str))
            except:
                pass
    return out_data
    
    
if __name__ == "__main__":
    out_data =   load_SIMB3_buoys()  
            
            
    
    