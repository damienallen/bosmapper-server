deploy:
	@echo "Deploying to bos.dallen.co"
	rsync -azP . root@188.166.69.34:/home/deploy/bosmapper/
