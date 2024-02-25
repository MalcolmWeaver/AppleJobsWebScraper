import requests
from bs4 import BeautifulSoup
import time
import re

class BaseJobsSiteScraper:

    def getAllJobUrls(self, soup) -> list[str]:
        raise NotImplementedError(self)
    def getJobUrl(self) -> str:
        raise NotImplementedError(self)
    
    def getJobTitle(self, soup) -> str:
        raise NotImplementedError(self)
    
    def getQualifications(self, soup) -> list[str]:
        raise NotImplementedError(self)
    
    def jobTitleIsEntryLevel(self, title: str) -> bool:
        """
        Check if the title could be for an entry level job.

        Returns:
        bool: false if the title implies Senior, Managerial, or lead, true otherwise
        """
        pattern = re.compile(r'[Ss]enior|[Mm]anager|[Ll]ead|[Ss]r|[Mm]ngr')
        isSeniorManagerialOrLead = pattern.search(title)
        return not isSeniorManagerialOrLead
    
    def qualificationsAreEntryLevel(self, qualifications):
        """
        Check if any of the qualifications indicate non entry level experience.
        
        Returns:
        bool: false if any of the qualifications indicate non entry level experience, true otherwise
        """
        # education and experience are not entry level if they contain "n(+) years of experience"
        pattern1 = re.compile(r'(?:one|two|three|four|five|six|seven|eight|nine|ten|\d{1,2})\s?(?:\+|plus|or more)?\s(?:year|yr)s?', re.IGNORECASE)

        # education and experience are not bachelors level if they mention graduate degrees without also including bachelor's degree"
        includesGrad = re.compile(r'(?:M\.?S\.?|Ph\.?\s?D\.?|[Mm]aster\'s|[Dd]octorate)')

        includesBachelors = re.compile(r'(BA|BS|Bachelor|BACHELOR)')

        for qualification in qualifications:
    
            if pattern1.search(qualification):
                return False
            if includesGrad.search(qualification) and not includesBachelors.search(qualification):
                return False
        return True
    
    def getEntryLevelPositionsFromList(self, allJobUrls : list[str], outputFilename="EntryLevelPositions.txt") -> int:
        # TODO: since date parameter
        """
        Retrieves entry level job positions from a list of job URLs and writes them to a file.
        Also prints progress to the console.

        Returns:
        int the number of entry level positions found
        """
        t0 = time.time()
        try:
            f = open(outputFilename, "a+")
            f.write(f"\nDate: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        except:
            print("failed to open file")
        

        numEntryLevelPositions = 0
        for idx, job in enumerate(allJobUrls):

            # Print progress every 20 jobs (there are  max 20 jobs per page)
            if (idx + 1 ) % 20 == 0:
                print(f"Processed {idx+1} jobs. Time elapsed: {time.time() - t0}.")
                print(f"Percent entry level: {numEntryLevelPositions / (idx+1) * 100}%. Percent complete: {(idx+1) / len(allJobUrls) * 100}%. Expected time remaining: {(len(allJobUrls) - (idx+1)) / (idx + 1) * (time.time() - t0)/60} minutes")
                f.flush()

            isEntryLevel = True

            # get the job description page
            jobUrl = self.getJobUrl(job)
            print("Job URL:", jobUrl)
            try:
                page = requests.get(jobUrl)
                if "The page you’re looking for can’t be" in page.text or "404 Not Found" in page.text:
                    print(f"Job URL {jobUrl} could not be found")
                    isEntryLevel = False
            except:
                print(f"Could not get page for {jobUrl}")
                continue
            soup = BeautifulSoup(page.content, "html.parser")

            # get the job title and check if it could be an entry level position
            title = ""
            try:
                title = self.getJobTitle(soup)    
            except:
                print(f"Could not get TITLE for {jobUrl}")

            if not self.jobTitleIsEntryLevel(title):
                print(f"Job title {title} is not for an entry level position")
                isEntryLevel = False

            # get the qualifications and check if they could be for an entry level position
            qualifications = []
            try:
                qualifications = self.getQualifications(soup)
                
            except:
                print(f"Could not get QUALIFICATIONS for {jobUrl}")
            if not self.qualificationsAreEntryLevel(qualifications):
                print(f"Qualifications are not for an entry level position")
                isEntryLevel = False
            # write to file
            if isEntryLevel:
                print(f"Entry level position found: {jobUrl}")
                f.write(f"{jobUrl}\n")
                numEntryLevelPositions += 1

        t1 = time.time()
        print(f"Time to get entry level positions: {t1-t0}")
        f.close()
        return numEntryLevelPositions

    def getEntryLevelPositions(self, onlyNew=False, isCached=False):
        """
        Retrieve all job URLs from the specified number of pages (all of them).
        """

        """
        Get the soup for the (first) page of query results.
        Get the number of pages for pagination.
        Optionally get all the job URLs from all pages and cache to a file, 
        or read from cached file.
        """

        if onlyNew:
            assert not isCached, "Cached data is not new data. Make sure if you select onlyNew, isCached is False."

        try:
            page = requests.get(self.jobsQueryURL)
            if "The page you’re looking for can’t be" in page.text:
                print(f"Job URL {self.jobsQueryURL} could not be found")
                exit()
        except:
            print(f"Could not get page for {self.jobsQueryURL}")
            exit()
        soup = BeautifulSoup(page.content, "html.parser")

        allJobUrls = []
        if isCached or onlyNew:
            # caching purposes (only about 0.1% change per hour)
            try:
                # get all job URLs from cached file
                f = open(self.jobTitlesCacheFilename, "r")
                allUrlsStr = f.read()
                allJobUrls = list(eval(allUrlsStr))
                print(f"There are {len(allJobUrls)} cached urls")
                f.close()
            except:
                print(f"Could not read cached file {self.jobTitlesCacheFilename}. Going to read from website")
                isCached = False
        
        if not isCached:
            
            if onlyNew:
                # get number of pages until you hit a repeat of the last 5 jobs (should have already collected)
                newJobUrls = self.getAllJobUrls(soup, onlyNew=onlyNew, last5Jobs=allJobUrls[:5])
                if newJobUrls == []:
                    print("No new jobs found")
                    return
                allJobUrls = newJobUrls
            else :
                # get number of pages for naive iteration
                allJobUrls = self.getAllJobUrls(soup, onlyNew=onlyNew)
            f = open(self.jobTitlesCacheFilename, "w")
            f.write(str(allJobUrls))
            print(f"{len(allJobUrls)} urls were cached")
            f.close()

        print(f"Beginning to scan for entry level positions. This may take a while. Check {self.outputFilename} for results...")
        self.getEntryLevelPositionsFromList(allJobUrls, self.outputFilename)    

class NewJobsSiteScraper(BaseJobsSiteScraper):
    """Only works if can sort by new"""
    def getAllJobUrls(self, soup, stopOnOldJobs=False, last5Jobs=[]) -> list[str]:
        raise NotImplementedError(self)