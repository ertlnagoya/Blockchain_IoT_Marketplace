import qs from 'querystring'

function verify(r) {
    var arg = r.variables.arg_name;
    if (arg == undefined) {
        var args = qs.parse(r.requestText);
        arg = args["name"];
    }
    arg.replace(/(-\d+\.ts|\.m3u8)$/gm,"");
    if (ngx.shared.keys.has(arg)){
        r.log("Auth success, key = " + arg);
        r.return(200);
        return;
    }
    r.log("Auth failed, key = " + arg);
    r.return(403)
}

function register(r) {
    var key = randomstr();
    ngx.shared.keys.add(key,"");
    r.log("Registered, key = " + key);
    r.return(200, key);
}

function randomstr() {
    var length = 32;
    const characters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQUSTUVWXYZ';
    let result = '';
    const charactersLength = characters.length;
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    return result;
}

export default {verify, register};
