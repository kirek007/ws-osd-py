![image](https://user-images.githubusercontent.com/1878027/210377476-0ca2a14e-71d7-40d8-add5-3d5d6f00a006.png)

# Tool for generating OSD for Walksnail DVR

That's easy, drag and drop files into UI, click Generate.
Then import generated sequence into and video editing software and adjust framerate to 60fps if needed.

# How to run

### Windows
Nothing to do, Go to [Release page](https://github.com/kirek007/ws-osd-py/releases)

### Linux / MacOS

Disclamer: I've tried my best to make it work on all systems, but it's only tested on Windows. So it might not work as expected 
on other systems.

**Only works with Python 3.10 due to issues with wxPython and python-opencv libs**

Install ffmpeg:

For Linux:
```bash
sudo apt install ffmpeg 
```

For MacOs:
```bash
brew install ffmpeg
```

Then clone respotiory and run app

```bash
git clone https://github.com/kirek007/ws-osd-py.git
cd ws-osd-py
make run
```

### CLI

Thanks to @odgrace it's now possible to run tool without GUI (which is quite complicated sometimes).
```bash
pip install -r requirements-noui.txt
python3 cli.py -h #It will list all required parameters
```


### Common issues for linux:
If there is an issue with `ModuleNotFoundError: No module named 'attrdict'` try to install wxPython from wheel.

Get packge link from here https://extras.wxpython.org/wxPython4/extras/linux/gtk3

eg. for Ubuntu 20: `https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04/wxPython-4.2.0-cp310-cp310-linux_x86_64.whl`

```bash
source .venv/bin/activate
pip install -f <link to package> wxPython
```

# Usage tutorial

https://www.youtube.com/watch?v=we3F4rIXTqU

# Fonts
You can get fancy fonts from [Sneaky_FPV](https://sites.google.com/view/sneaky-fpv/home?pli=1), or get [default walksnails fonts](https://drive.google.com/file/d/1c3CRgXYQaM3Tt4ukLSIvoogScQZs9w49/view)

# Examples
Here are some results:

https://www.youtube.com/watch?v=fHHXh9k-SGg

https://www.youtube.com/watch?v=2u7wiJBIdCg

# Ack
Software is provided as is and it is open sourced so contributions are welcome! 

Feel free to create a ticket in case something is not working. 


## Coffee needed
If you like tool, you can buy me a coffee so keep working more overnights :) 

<a href="https://www.buymeacoffee.com/kirek" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 30px !important;width: 108 !important;" ></a>
