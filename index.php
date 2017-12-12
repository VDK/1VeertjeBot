<?php
include_once('variables.php');
include_once('ttrssapi.php');
require_once( __DIR__ . '/vendor/autoload.php' );
use Mediawiki\Api\SimpleRequest;
// Log in to a wiki
$api = new \Mediawiki\Api\MediawikiApi( 'https://commons.wikimedia.org/w/api.php' );
$api->login( new \Mediawiki\Api\ApiUser( $wpusername, $wppassword ) );


//update RSS feed
$trss = new TTRSSAPI( $url_to_ttrss, $tts_username, $tts_password);
$trss ->updateFeed($video2commonsRSSid);


// Create connection
$conn = new mysqli($servername, $username, $password, $dbname);
mysqli_set_charset($conn, 'utf8');
// Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
} 


$sql = "SELECT id, title FROM ttrss_entries where entry_read = 0 ";
$result = $conn->query($sql);

if ($result->num_rows > 0) {
    // output data of each row
    while($row = $result->fetch_assoc()) {
    	$common_name = false;
    	$mark_read = false;
        $category = array();
	    $content = json_decode(file_get_contents("https://commons.wikimedia.org/w/api.php?action=parse&contentmodel=wikitext&format=json&page=File:".urlencode(str_replace(" ", "_", $row['title']))), true);
        if (isset($content['error'])){
            $mark_read = true;
        }
        elseif (isset($content["parse"])) {          
        
    	    $existingCategories = $content["parse"]["categories"];
    	 	$pageid 	        = $content['parse']['pageid'];
    	 	
    	 	//find YouTube channel_id/username
    	 	foreach ($content["parse"]["externallinks"] as $key => $value) {
    	 		if (preg_match('/(https?:\/\/|)(www\.|)?youtube\.com\/(channel|user)\/([a-zA-Z0-9\-]+)/', $value, $matches)){
    	 			$common_name = getCommonName($conn, $matches[3], $matches[4]);
    	 			break;
    	 		}	
    	 	}
    	 	//get pubdate
            $content = json_decode(file_get_contents("https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=extmetadata&format=json&pageids=".$pageid), true);
        	$pubdate = $content['query']['pages'][$pageid]['imageinfo'][0]['extmetadata']['DateTimeOriginal']['value'];
            if (strlen($pubdate) == 4){
                $pubdate = $pubdate."-01-01";
            }
            $pubdate = strtotime($pubdate);

            //RN7 specific code
        	if ($common_name == 'RN7'){
                if( $pubdate < date(strtotime('2017-11-01'))){
    			     $common_name = 'N1';
                }
                $category =  getRN7Cats(
                    $content['query']['pages'][$pageid]['imageinfo'][0]['extmetadata']['ObjectName']['value']." ".
                    $content['query']['pages'][$pageid]['imageinfo'][0]['extmetadata']['ImageDescription']['value'],  $pubdate );
                var_dump($category);
    		}
            //is it needed to add category?
            foreach ($existingCategories as $key => $xcategory) {
            	$xcategory = $xcategory['*'];
            	
            	if ($common_name && preg_match('/^'.$common_name.'_videos_in_'.date('Y',$pubdate).'/',$xcategory)){
        			$mark_read = true;
        			break;
            	}
                elseif (preg_match('/.*[vV]ideos_.+'.date('Y',$pubdate).'/',$xcategory)){
                    $mark_read = true;
                    break;
                }
            }
            if (!$mark_read){
            	
                if ($common_name){
                   $category[] = "\n[[Category:".$common_name." videos in ".date('Y',$pubdate)."|".date('md',$pubdate)."]]";
                }
                else{
            	   $category[] = "\n[[Category:Videos of ".date('Y',$pubdate)."|".date('md',$pubdate)."]]";

                }

            	$category2 = stripSortKey($category);


                if (date('md', $pubdate) == '0101'){
                    //no sortkey if date is January 1st. Probably not an accurate date.
                    $category = $category2;
                }
            	
            	try{
        			$response = $api->postRequest( new SimpleRequest( 'edit',  
                    // var_dump(
                        array('pageid'    => $pageid, 
                              'token' => $api->getToken(), 
                              'appendtext' => implode("\n", $category), 
                              'summary'    => "Added ".implode(", ", $category2), 
                              'bot' => true, 
                              'nocreate' => true, 
                              'redirect' => true )
                               ) 
                        );
                    if ($response['edit']['result'] == 'Success'){
                        $mark_read = true;
                    }

    			}
    			catch ( UsageException $e ) {
    			    echo "The api returned an error!";
    			}
            }
        }

        if ($mark_read == true){
        	$conn->query("UPDATE ttrss_entries set entry_read = 1 where id =".$row['id']);
        }

    }
} else {
    echo "0 results";
}


$conn->close();

function getRN7Cats($teststring, $pubdate ){
    if (strpos($teststring, "Nijmegen" ,1) || strpos($teststring, "Nijmeegse",1) ){
        $cat[] = "[[Category:Videos of ".date('Y', $pubdate)." from Nijmegen|".date('md', $pubdate)."]]";
    }

    $needles = array('Arnhem', 'Druten', 'Heumen', 'Montferland', 'Oude IJsselstreek', 'Rijnwaarden', 'Wijchen', 'Zevenaar');

    foreach($needles as $needle) {
        if ( strpos($teststring, $needle)){
            $cat[] = "[[Category:Videos from ".$needle."|".date('Ymd', $pubdate)."]]";
        }
    }
    return $cat;

}

function stripSortKey($input){
    $output = array();
    if (!is_array($input)){
        $input = array($input);
    }
    foreach ($input as $value) {
        $output[] = preg_replace('/\[\[(.+)\|.+\]\]/i', '[[$1]]', $value);
    }
    return $output;
}
function getCommonName($conn, $label, $name){
    if ($label == 'channel'){
        $label = 'channel_id';
    }
    else{
        $label = 'youtube_username';
    }
    $sql = 'SELECT common_name from youtube_channels WHERE '.$label.' = "'.mysqli_real_escape_string($conn, $name).'"';
    $result = $conn->query($sql);
    if ($result ) {
        $row = $result->fetch_assoc();
        return $row['common_name'];
    }
    else{
        return false;
    }

}
?>
