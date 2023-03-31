# This script contains the code for Python Selenium-based web scraper of Pharos: https://pharos.nih.gov/


import pandas
import os
import zipfile


from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.firefox.options import Options

#PATH_logs = "C:\\WORK\\Pfizer-project\\Update_2023\\Pharos_Parser_Py\\driver_logs.txt"
#PATH_downloads = "C:\\WORK\\Pfizer-project\\Update_2023\\Pharos_Parser_Py\\Downloads"


class SeleniumPharosParser:
    """
    This class contains all function to extract data from Pharos https://pharos.nih.gov/
    Pharos basic API is not useful, whereas full data requires to use SQL and sufficient storage
    Use this class if you want to extract only a fraction of Pharos data for a small number of targets

    Some of the class methods reset the working directory -> reset it with os.chdir(...)

    Dependencies:
    -Web browser and its driver for selenium: https://selenium-python.readthedocs.io/index.html
    -pip install selenium
    -pip install pandas
    """

    # Class Variables
    PHAROS_URL = "https://pharos.nih.gov/"



    def __init__(self, PATH_logs, PATH_downloads, binary_path):
        self.driver_logs = PATH_logs
        self.downloads_folder = PATH_downloads
        self.binary_path = binary_path

    def initialize_session(self):
        ops = Options()
        ops.binary_location = self.binary_path
        profile = webdriver.FirefoxProfile()
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.download.manager.showWhenStarting", False)
        profile.set_preference("browser.download.dir", self.downloads_folder)
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/x-gzip")
        driver = webdriver.Firefox(
                    service_log_path=self.driver_logs,
                    firefox_profile=profile,
                    options=ops)
        driver.implicitly_wait(1)
        self.driver = driver

    def parse_one_target_ligand(self, pharos_target_url):
        driver = self.driver

        # Go to target
        driver.get(pharos_target_url)
        sleep(10)

        driver_alert = Alert(driver)

        try:
            # No error -> target is likely FALSE
            driver_alert.text
            message = "Alert at " + pharos_target_url
            driver_alert.accept()
            return(message)
        except:
            # In most cases driver_alert.text will produce nothing and we simply proceed
            pass

        # Removing popups
        try:
            driver.find_element(By.CLASS_NAME, "shepherd-cancel-icon").click()
            sleep(2)
        except :
            # Pop-up did-not appear, do nothing
            pass

        try:
            driver.find_element(By.CLASS_NAME, "shepherd-cancel-icon").click()
        except :
            # Pop-up did-not appear, do nothing
            pass

        # Click Download
        driver.find_element(By.XPATH, 
                            '/html/body/app-root/main/div/pharos-main/pharos-target-header/article/div/div/div[3]/button').click()
        sleep(1)

        # Click Drugs and Ligands
        all_download_buttons = driver.find_elements(By.CLASS_NAME, 
                            'mat-checkbox-layout')

        def get_correct_element(element):
            if element.text == 'Drugs and Ligands':
                return element

        needed_text = map(get_correct_element, all_download_buttons)
        needed_text = list(needed_text)
        needed_text = [x for x in needed_text if x is not None]

        try:
            needed_text[0].click()
        except:
            # The step failed and maybe we were too fast
            # Rerun the whole steps again
            sleep(10)
            try:
                driver.find_element(By.CLASS_NAME, "shepherd-cancel-icon").click()
                sleep(2)
            except :
                # Pop-up did-not appear, do nothing
                pass

            try:
                driver.find_element(By.CLASS_NAME, "shepherd-cancel-icon").click()
            except :
                # Pop-up did-not appear, do nothing
                pass

            # Click Download
            driver.find_element(By.XPATH, 
                                '/html/body/app-root/main/div/pharos-main/pharos-target-header/article/div/div/div[3]/button').click()
            sleep(1)

            # Click Drugs and Ligands
            all_download_buttons = driver.find_elements(By.CLASS_NAME, 
                                'mat-checkbox-layout')

            def get_correct_element(element):
                if element.text == 'Drugs and Ligands':
                    return element

            needed_text = map(get_correct_element, all_download_buttons)
            needed_text = list(needed_text)
            needed_text = [x for x in needed_text if x is not None]
            needed_text[0].click()


        # Click Download
        final_download_button = driver.find_elements(By.TAG_NAME, 
                            'button')
        def get_correct_final_button(element):
            if element.text == 'Run Download Query':
                return element
            
        final_download_button = map(get_correct_final_button, final_download_button)
        final_download_button = list(final_download_button)
        final_download_button = [x for x in final_download_button if x is not None]
        final_download_button[0].click()


        # Waiting to download
        files = os.listdir(self.downloads_folder)
        while "pharos data download.zip" not in files:
            sleep(0.5)
            files = os.listdir(self.downloads_folder)

        # Unzip file
        os.chdir(self.downloads_folder)
        os.rename("pharos data download.zip", "pharos_data_download.zip")

        zip_file = self.downloads_folder + "\\" + "pharos_data_download.zip"

        with zipfile.ZipFile(zip_file,"r") as zip_ref:
            zip_ref.extractall(self.downloads_folder)

        # Remove old stuff
        os.remove("pharos_data_download.zip")
        os.remove("query metadata.txt")

        # Import data into pandas
        dataset = pandas.read_csv("query results.csv")
        uniprotID = dataset["UniProt"]
        uniprotID = uniprotID.iloc[0]

        # Saving under new file name
        new_filename = self.downloads_folder + "\\" + uniprotID + ".csv"
        dataset.to_csv(new_filename)
        os.remove("query results.csv")


    def parse_targets_from_file(self, file_path):
        # Preparing file inputs
        file = open(file_path)
        genes_to_parse = file.readlines()

        # Curating strings
        genes_to_parse = [x.replace("\n", "") for x in genes_to_parse]

        # Preparing urls
        genes_to_parse = [self.PHAROS_URL + "/targets/" + x for x in genes_to_parse]

        for x in genes_to_parse:
            try:
                self.parse_one_target_ligand(x)
                sleep(0.5)
            except:
                # Not safe at the moment (improve later)
                self.parse_one_target_ligand(x)
                sleep(0.5)

        # Get datasets and concatenate them
        filenames = [os.path.join(self.downloads_folder, file) for file in os.listdir(self.downloads_folder)]

        datasets = []
        for filename in filenames:
            datasets.append(pandas.read_csv(filename))

        # Concatenate all data into one DataFrame
        drug_target_frame = pandas.concat(datasets, ignore_index=True)
        drug_target_frame.to_csv("drug_target_frame.csv", sep = ";")

    
    def close_all(self):
        self.driver.close()
