# start_chia

This utility for control process chia ploting 


Web Interface for utility

Automaticaly restart

Internal task query with manege

Ploting statistics




For start configuration use "config.ini" file in same directory.

Configuration parameters:

Section "default" is template and global parameters

[default]
chia_path - path for chia.exe cli utulity (if empty, program try fint utility automaticaly)

thread_per_plot - number of thread per plot process

parallel_plot - if parallel_plot > 1 then create paralel process with same configs

temp_dir - temp dir for ploting

work_dir - dir where complete file 

memory - memory limit in mb for one process

bucket - number ob backet

k_size - K size

plots_count - number of plots for creation

auto_restart - true/false restart process when plots_count riched, default = False 

auto_find_exe - true/false automaticaly find chia cli util, default = True 

pause_before_start - true/false pause before first plot creation start, default = 0 

recheck_work_dir - true/false if set true add dir to farmer, default = False 

fingerprint - chia wallet fingerprint

pool_pub_key - chia pool public key

farmer_pub_key - chia wallet public key

start_node - true/false if true start node (chia start node)

set_peer_address - if not empty exec command "chia configuration --set_peer_address <address:port>"

start_shell - true/false exec command in shell proess

shell_name - shell name, default 'powershell'

p_open_shell true/false parameters for subprocess command, default = False 

code_page - console code page, default cp1251

bitfield_disable true/false - use bitfield options default = False


For every process need create section with any name (not default)
like [pool-1]
in this section your may redifine global options
