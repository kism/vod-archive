if [ -z "$2" ]; then
    echo "Usage:"
    echo "./gettwitchbeartoken.sh <client id> <client secret>"
    echo ""
    echo "You will need to create a 'twitch app'"
    echo "https://dev.twitch.tv/console/apps/create"
    echo "Need to enable 2fa for your account"
    echo "Oauth URL can be https://localhost"
    exit 1
fi


client=$1
secret=$2

url="https://id.twitch.tv/oauth2/token?client_id=${client}&client_secret=${secret}&grant_type=client_credentials"

echo $url

curl --location --request POST $url