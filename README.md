https://medium.com/@khushbu.parakh/create-instances-in-google-cloud-with-private-image-328409916744

<p> Bucket Name: Name of the bucket you want </p>
<p> Subnetwork: Subnetwork you want your instance to be in. </p>
<p>Source_file_name: Path to your private image.</p>
<p> Destination_blob_name: Any name needs to in gzip format. </p>
<p> Projectid: Your project id. </p>
<p> Zone: You want to create your instance in. </p>
<p> Machine Type: Standard machine type with 4 vCPUs and 15 GB of memory. (n1-standard4)</p>
<p> Instance-name: Name of your instance </p> 
<br>
Before running the script edit the network details in script. To whatever network you have in your cloud. 
Please make sure you do 

 pip install 

- google-api-python-client
- oauth2client
- google-auth
- google-auth-httplib2
- google-cloud-storage
- google-resumable-media

To run the script 

```
python instance.py  --bucket_name somebucketname --subnetwork somesubnework --source_file_name path/gcp_controller.tar.gz  --destination_blob_name gcp_controller.tar.gz --project projectid --zone zonename --machine-type n1-standard4 --instance-name
test-instances
```
