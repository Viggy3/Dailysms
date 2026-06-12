from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/reply_sms", methods=['POST'])
def reply_sms():
    # Create a new Twilio MessagingResponse
    resp = MessagingResponse()
    resp.message("The Robots are coming! Head for the hills!")

    # Return the TwiML (as XML) response
    return Response(str(resp), mimetype='text/xml')

if __name__ == "__main__":
    app.run(port=3000)