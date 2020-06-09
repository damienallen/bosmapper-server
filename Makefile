deploy:
	@echo "Deploying to bos.dallen.co"
	rsync -azP . root@188.166.69.34:/home/deploy/bosmapper/

draw:
	export DISPLAY=:99.0
	Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
	python export/draw.py
