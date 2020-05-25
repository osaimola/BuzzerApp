/**
 *  Simple Menu Template
 *
 *  This Function builds a simple IVR menu. Learn more about <Gather> at:
 *  https://www.twilio.com/docs/api/twiml/gather
 */
exports.handler = function(context, event, callback) {
  let twiml = new Twilio.twiml.VoiceResponse();

  /* this is triggered when DTMF tones are present
    pass to api endpoint and process the response grant access or not */
  if (event.Digits) {
    var fetch = require("node-fetch");
    var body = {
      Digits: event.Digits
    };
    fetch(
      "https://gugjo00u3b.execute-api.us-east-1.amazonaws.com/default/buzzerApp",
      {
        method: "post",
        body: JSON.stringify(body),
        headers: { "Content-Type": "application/json" }
      }
    ).then(response => {
      response.text().then(text => {
        // handle response content
        switch (text) {
          case "master":
            twiml.say("Welcome back");
            twiml.play({
              digits: "9"
            });
            callback(null, twiml);
            break;
          case "friend":
            twiml.say("Door's open!");
            twiml.play({
              digits: "w9"
            });
            callback(null, twiml);
            break;
          case "stranger":
            twiml.say("Sorry, wrong code. Goodbye");
            callback(null, twiml);
            break;
          default:
            twiml.say("Something went wrong. Contact Osa.");
            callback(null, twiml);
        }
      });
    });
  } else {
    /* this will run when a call first comes in
      play message to request DTMF tones and return codes to this function*/
    twiml
      .gather({ numDigits: 4 })
      .say(
        "Hi. Enter a 4 digit pin. Or, 0 followed by the pound key to request access."
      );
    callback(null, twiml);
  }
};
