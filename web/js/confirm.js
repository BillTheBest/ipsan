Showbo.Msg.confirm('х╥хои╬ЁЩ',function(flag){
                    if(flag=='yes'){
                        for(i=0;i<id.length;i++){
                            var data = {
                                "id" : id[i]
                            };
                            var r = ajax_http("users/"+id[i]+"/delete","post",data,output_delete);                    
                        }
                        if(!r){
                            alert("Reqeust failure");
                        }
                    }else if(flag=='no'){
                        return false;
                    }
                });