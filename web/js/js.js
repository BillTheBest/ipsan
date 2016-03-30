var api_server = "192.168.1.169";
var dict = {};

$(function() {
    registerWords();
    setLanguage(getLanguage());
});


function setLanguage(lang) {
    setLangCookie("lang=" + lang + "; path=/;");
    translate();
}

function getLanguage() {
    var lang = getCookieVal("lang");
    if (lang == null)
        lang = "en";
    return lang;
}

function getCookieVal(name) {
    var items = document.cookie.split(";");
    for (var i in items) {
        var cookie = $.trim(items[i]);
        var eqIdx = cookie.indexOf("=");
        var key = cookie.substring(0, eqIdx);
        if (name == $.trim(key)) {
            return $.trim(cookie.substring(eqIdx+1));
        }
    }
    return null;
}

function setLangCookie(cookie) {
    document.cookie = cookie;
}

function translate() {
    loadDict();
    
    $("[lang]").each(function() {
        switch (this.tagName.toLowerCase()) {
            case "input":
                $(this).val( __tr($(this).attr("lang")) );
                break;
            default:
                $(this).text( __tr($(this).attr("lang")) );
        }
    });
}

function __tr(src) {
    return (dict[src] || src);
}

function loadDict() {
    var lang = (getCookieVal("lang") || "en");
    var url = "http://"+api_server+"/" + lang + ".json";
    $.support.cors = true;
    $.ajax({
        async: false,
        type: "GET",
        url: url, //lang + ".json",
        success: function(msg) {
            dict = eval(msg);
        }
    });
}

function registerWords() {
    $("[lang]").each(function() {
        switch (this.tagName.toLowerCase()) {
            case "input":
                $(this).attr("lang", $(this).val());
                break;
            default:
                $(this).attr("lang", $(this).text());
        }
    });
}


/* string format prototype */
String.format = function(src){  
    if (arguments.length == 0) return null;  
    var args = Array.prototype.slice.call(arguments, 1);  
    return src.replace(/\{(\d+)\}/g, function(m, i){  
        return args[i];  
    });  
};

/*cookie*/
function getCookie(c_name){
    if (document.cookie.length>0)
    { 
        c_start=document.cookie.indexOf(c_name + "=");
        if (c_start!=-1)
        { 
            c_start=c_start + c_name.length+1 ;
            c_end=document.cookie.indexOf(";",c_start);
            if (c_end==-1) c_end=document.cookie.length
            return unescape(document.cookie.substring(c_start,c_end));
        } 
    }
    return null;
    }
function setCookie(c_name,value,expiredays)
{
    var exdate=new Date();
    exdate.setDate(exdate.getDate()+expiredays);
    document.cookie=c_name+ "=" +escape(value)+
    ((expiredays==null) ? "" : "; expires="+exdate.toGMTString());
}

function readcookie(){
    var username=getCookie('username');
    if (username!=null && username!="")
    {
        return true;
    }
    else 
    {
        window.parent.location.href="index.html";
        return false;
    }
}

/* do ajax http request */
function ajax_http(name, method, data, callback){
    var url = "http://"+api_server+":8000/api/" + name;
    $.support.cors = true;
    if (method.toLowerCase() == "get")
    {
    $.ajax( {
            url : url,
            cache : false,
            dataType : "json", 
            type : method, 
            success:function(data) { 
                callback(data);
            }
        });
    }
    else if (method.toLowerCase() == "post")
    {
    $.ajax( {
            url : url,
            dataType : "json", 
            type : method, 
            data: data,
            success:function(data) {                 
                callback(data);
            }
        });
    }
    else{
    return false; /* unsupport method */
    }
    return true;
 }

/*time*/
function Time(time_at){
    var time = (time_at)*1000;
    var datetime = new Date(time);
    var yyyy = datetime.getFullYear();
    var MM = datetime.getMonth()+1;
    var dd = datetime.getDate();
    var hh = datetime.getHours();
    var mm = datetime.getMinutes();
    var ss = datetime.getSeconds();
    if(hh<10){
        hh="0"+hh;
    }
    if(mm<10){
        mm="0"+mm;
    }
    if (ss<10) {
        ss="0"+ss;
    }
    var date = yyyy+"-"+MM+"-"+dd+"&nbsp;"+hh+":"+mm+":"+ss;
    return date;
}

/*size*/
function human_size(size,kb) {
    var unit = ['K', 'M', 'G', 'T', 'P'];
    var multiple = 1024;

    if (kb){
        size *= 1024;
    }
    if (size < multiple){
        return size + "Bytes";
    }
    for (var i = 0; i<unit.length; ++i)
    {
        size = size / multiple;
        if (size < multiple){
            return (Math.floor(size*10)/10)+unit[i];
        }
    }
}

/*checkbox*/
function checked(num){
    var id=[];
    var j=0;
    for(i=0;i<num;i++){        
        var operationn = "operation"+i;
        if(document.getElementById(operationn).checked){
            id[j]=document.getElementById(operationn).value;
            j=j+1;
        }
    }
    return id;
}

function get_checked_byname(name){
	var ids = [];
	var i = 0;
	$("input[type=checkbox][name="+ name + "]").each(function(){
		if (this.checked){
			ids[i] = this.id;
			i+=1;
		}
	});
	return ids;
}

function get_checked_ids(){
	var ids = [];
	var i = 0;
	$("input[type=checkbox]:checked").each(function(){
		ids[i] = this.id;
			i+=1;
	});
	return ids;
}

function alert_info(newclass,text){
    $("#message").attr('class', newclass);                     
    $("#message").text(text);
    $("#message").show().delay(1500).fadeOut();
}

/*check username*/
function chk_username(name){
    var usern = /^[a-zA-Z0-9_]{1,}$/; 
    if (!usern.test(name)) {
        var tip = "用户名只能由字母数字下划线组成"; 
        return tip;
    }    
}

/*兼容trim*/
String.prototype.trim = function(){ return Trim(this);};
function LTrim(str)
{
 

   var i;
    for(i=0;i<str.length;i++)
    {
        if(str.charAt(i)!=" "&&str.charAt(i)!=" ")break;
    }
    str=str.substring(i,str.length);
    return str;
}
function RTrim(str)
{
    var i;
    for(i=str.length-1;i>=0;i--)
    {
        if(str.charAt(i)!=" "&&str.charAt(i)!=" ")break;
    }
    str=str.substring(0,i+1);
    return str;
}
function Trim(str)
{
    return LTrim(RTrim(str));
}


