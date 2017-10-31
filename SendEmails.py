"""
Class clsSendEmail
  
  Description: 
    A Python script to send emails from a gmail account.
    Important info on the account: 
  
  Author and contact: 
    W. Heidorn Iowa State Univiersity, USA wheidorn@iastate.edu
  
  Notes:
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class clsSendEmails :
  """
    This will send out notification emails during operations
  """

  def funcSendMail(self, strRecipient, strSubject, strMessage):
    """
      recipient must be of the form 'username@domain.com'
    """
    gmailUser = 'ISUChillerControl@gmail.com' #A valid gmail account
    gmailPassword = 'ISUphysics2017'          #That account's password
   

    msg = MIMEMultipart()
    msg['From'] = gmailUser
    msg['To'] = strRecipient
    msg['Subject'] = 'ISUChillerControl: '+ strSubject
    msg.attach(MIMEText(strMessage))

    mailServer = smtplib.SMTP('smtp.gmail.com', 587)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(gmailUser, gmailPassword)
    mailServer.sendmail(gmailUser,strRecipient, msg.as_string())
    mailServer.close()

#if __name__ == '__main__':
#  clsSendEmails.send_mail(clsSendEmails,'wheidorn@gmail.com','Test','This is a test of the chiller emergency broadcast system')
