FROM python:3.6
RUN pip install requests
ADD statuspage.py statuspage.py
CMD ["python", "statuspage.py"]
