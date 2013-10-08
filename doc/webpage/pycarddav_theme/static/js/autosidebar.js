jQuery.fn.justtext = function() {
    return $(this).clone()
            .children()
            .remove()
            .end()
            .text();
 
};

$(document).ready(function(){
   $("h1").each(function(){
        $("#sidebar").append(
            "<li class=\"nav-header\"><h4>"+$(this).children()[0].justtext()+"</h4></li>"
        );
        ul = $("<ul>");
        $("h2",$(this).parent().parent()).each(function(){
            ul.append(
            "<li class=\"nav-header\"><h5>"+$(this).justtext()+"</h5></li>"
            );
            subul = $("<ul>");
            $("h3",$(this).parent()).each(function(){
                subul.append(
                "<li class=\"nav-header\"><h6>"+$(this).justtext()+"</h6></li>"
                );
            });
            ul.append(subul);
        });
        $("#sidebar").append(ul);
   });
});