from selenium import webdriver
from webdriver_recorder import Recorder

recorder = Recorder()
browser = recorder.start(webdriver.Firefox())
try:
    browser.get('http://il.pycon.org/2016/')

    signup_link = browser.find_element_by_link_text('sign up to our list')
    link_location = signup_link.location
    scroll_script = "scrollTo({},{})".format(link_location['x'], link_location['y'] - 70)
    browser.execute_script(scroll_script)

    signup_link.click()

    browser.find_element_by_class_name('btn-waitlist').click()

    browser.find_element_by_id('waitlisted_person_name').send_keys('Selenium WebDriver')

finally:
    recorder.close()
    browser.quit()
    print(recorder.export())
