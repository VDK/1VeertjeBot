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
        $category_patterns = false;
        $categories = array();

        preg_match('/\.[^\.]+$/i',$row['title'],$ext);

        if ($ext[0] == '.webm' || $ext[0] == '.ogv'){
           $content = json_decode(file_get_contents("https://commons.wikimedia.org/w/api.php?action=parse&contentmodel=wikitext&format=json&page=File:".urlencode(str_replace(" ", "_", $row['title']))), true);
        }
        else{
            $mark_read = true;
        }
        if (isset($content['error']) ){
            $mark_read = true;
        }
        if (isset($content["parse"]) && !$mark_read) {          
        
            $existingCategories = $content["parse"]["categories"];
            $pageid             = $content['parse']['pageid'];
            
            
            //find YouTube channel_id/username
            foreach ($content["parse"]["externallinks"] as $key => $value) {
                if (preg_match('/(https?:\/\/|)(www\.|)?youtube\.com\/(channel|user)\/([a-zA-Z0-9\-]+)/', $value, $matches)){
                    $common_name = getCommonName($conn, $matches[3], $matches[4]);
                    $category_patterns = getCategoryPatterns($conn, $matches[3], $matches[4]);
                    break;
                }   
            }
            //get pubdate
            $content = json_decode(file_get_contents("https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=extmetadata&format=json&pageids=".$pageid), true);

            $pubdate = $content['query']['pages'][$pageid]['imageinfo'][0]['extmetadata']['DateTimeOriginal']['value'];
            if (strlen($pubdate) == 4){
                $pubdate = $pubdate."-01-01";
            }
            if (!strtotime($pubdate)){
                if(preg_match('/(20|19|18)[0-9]{2}.[0-9]{2}.[0-9]{2}/', $pubdate, $matches)){
                    $pubdate = $matches[0];
                }
                elseif(preg_match('/[0-9]{2}.[0-9]{2}.(20|19|18)[0-9]{2}/', $pubdate, $matches)){
                    $pubdate = $matches[0];
                }
                elseif(preg_match('/(20|19|18)[0-9]{2}/', $pubdate, $matches)){
                    $pubdate = $matches[0].'-01-01';
                }
                else{
                    $mark_read = true;
                }

            }
            $pubdate = strtotime($pubdate);

            
           if ($category_patterns){
                $keys = array(
                    '%Ymd'  => date('Ymd',  $pubdate),
                    '%md'   => date('md',   $pubdate),
                    '%Y'    => date('Y',    $pubdate),
                    '%F'    => date('F',    $pubdate));

                foreach ($category_patterns as $category_pattern) {
                    if (preg_match(
                        '/\b'.strtolower($category_pattern['needle']).'\b/', strtolower(
                        $content['query']['pages'][$pageid]['imageinfo'][0]['extmetadata']['ObjectName']['value']." ".
                        $content['query']['pages'][$pageid]['imageinfo'][0]['extmetadata']['ImageDescription']['value']))){
                            $categories[] = '[[Category:'.str_replace(array_keys($keys), array_values($keys), $category_pattern['pattern']).']]';
                    }
                }
            }

            //RN7 specific code
            if ($common_name == 'RN7' && $pubdate < date(strtotime('2017-11-01'))){
                foreach ($categories as $key => $value) {
                    $categories[$key] = str_replace('RN7', 'N1', $value);
                }
            }
            //is it needed to add category?
            foreach ($existingCategories as $key => $xcategory) {
                $xcategory = $xcategory["*"];

                if ($category_patterns){
                    foreach ($categories as $key => $category) {
                        if(strpos($category, str_replace('_', ' ', $xcategory))){
                            unset($categories[$key]);
                        }
                    }
                }
                elseif(preg_match('/.*[vV]ideos_.+'.date('Y',$pubdate).'/',$xcategory)){
                    $mark_read = true;
                    break;
                }
            }
            if (!$mark_read){
                
                if (!$category_patterns){
                   $categories[] = "\n[[Category:Videos of ".date('Y',$pubdate)."|".date('md',$pubdate)."]]";

                }
				$categories = array_unique($categories);

                $categories2 = stripSortKey($categories);


                if (date('md', $pubdate) == '0101'){
                    //no sortkey if date is January 1st. Probably not an accurate date.
                    $categories = $categories2;
                }
                
                try{
                    $response = $api->postRequest( new SimpleRequest( 'edit',  
                    // var_dump(
                        array('pageid'    => $pageid, 
                              'token' => $api->getToken(), 
                              'appendtext' => implode("\n", $categories), 
                              'summary'    => "Added ".implode(", ", $categories2), 
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

function stripSortKey($input){
    $output = array();
    if (!is_array($input)){
        $input = array($input);
    }
    foreach ($input as $key => $value) {
        $output[$key] = preg_replace('/\[\[(.+)\|.+\]\]/i', '[[$1]]', $value);
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

function getCategoryPatterns($conn, $label, $name){
    if ($label == 'channel'){
        $label = 'channel_id';
    }
    else{
        $label = 'youtube_username';
    }
    $patterns = array();
    $sql = 'SELECT needle, pattern from channel_patterns LEFT JOIN youtube_channels USING (channel_id) WHERE '.$label.' = "'.mysqli_real_escape_string($conn, $name).'"';
    $result = $conn->query($sql);
    if ($result) {
        while($row = $result->fetch_assoc()) {
            $patterns[] = array('needle'=> $row['needle'], 'pattern' => $row['pattern']);
        }
        return $patterns;
    }
    else{
        return false;
    }

}

?>
